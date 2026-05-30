import functools
from datetime import timedelta

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app import auth, config
from app.database import backup_database, export_json_snapshot, init_db
from app.services import exportacao as svc_exportacao
from app.services import metricas_gestor as svc_mgestor
from app.services import tratativas as svc_tratativas
from app.services import vendas_performance as svc_perf
from app.services import vendas_tratativa as svc_vtrat
from app.utils.cache import get as cache_get
from app.utils.datetime_br import agora, formatar
from app.utils.realtime import versao_atual
from app.validators import (
    validar_tratativa_situacao,
    validar_venda_performance,
    validar_venda_tratativa,
)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = config.SECRET_KEY
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
    if config.IS_CLOUD:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.config["DB_ERROR"] = None
    _db_ok = {"ready": False}

    def _ensure_db() -> bool:
        if _db_ok["ready"]:
            return True
        if app.config["DB_ERROR"]:
            return False
        try:
            init_db()
            _db_ok["ready"] = True
            return True
        except Exception as exc:
            app.config["DB_ERROR"] = str(exc)
            import sys

            print(f"[ERRO BANCO] {exc}", file=sys.stderr, flush=True)
            return False

    def _usuario_sessao() -> dict:
        return session.get("usuario") or {}

    def _escopo_operador() -> str | None:
        """None = todos (gestor). ID = filtrar por operador."""
        u = _usuario_sessao()
        if u.get("is_gestor"):
            op = request.args.get("operador", "").strip()
            if op in auth.OPERADORES_IDS:
                return op
            return None
        return u.get("id")

    def _registrado_por_atual() -> str:
        return _usuario_sessao().get("id", "mayara")

    def _contagens():
        def factory():
            op = None
            u = session.get("usuario") or {}
            if not u.get("is_gestor"):
                op = u.get("id")
            m_trat = svc_tratativas.metricas(registrado_por=op)
            m_perf = svc_perf.metricas(registrado_por=op)
            return {
                "tratativas_abertas": m_trat.get("em_andamento", 0),
                "performance_em_andamento": m_perf.get("em_andamento", 0),
                "performance_perdidos": m_perf.get("perdidos", 0),
            }

        return cache_get("contagens", factory)

    @app.after_request
    def _security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        if config.IS_CLOUD:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.before_request
    def _require_db():
        if request.endpoint in ("health", "static"):
            return None
        if request.endpoint and request.endpoint.startswith("static"):
            return None
        if not _ensure_db():
            return (
                render_template(
                    "erro_banco.html",
                    erro=app.config["DB_ERROR"],
                    tem_url=bool(config.DATABASE_URL),
                ),
                503,
            )
        return None

    @app.context_processor
    def inject_globals():
        def moeda(valor):
            if valor is None:
                return "—"
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        contagens = _contagens() if session.get("autenticado") else {}
        return {
            "config": config,
            "moeda": moeda,
            "formatar_data": formatar,
            "is_cloud": config.IS_CLOUD,
            "usuario": session.get("usuario"),
            "contagens": contagens,
            "sync_version": versao_atual() if session.get("autenticado") else "",
        }

    def login_required(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("autenticado"):
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    @app.route("/health")
    def health():
        db = "ok" if _ensure_db() else "erro"
        return jsonify({"status": "ok", "database": db, "hora_br": agora().isoformat()}), 200

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("autenticado"):
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            usuario_id = request.form.get("usuario", "").strip()
            senha = request.form.get("senha", "")
            dados = auth.autenticar(usuario_id, senha)
            if dados:
                session.clear()
                session.permanent = True
                session["autenticado"] = True
                session["usuario"] = dados
                return redirect(url_for("dashboard"))
            flash("Usuário ou senha incorretos.", "erro")
        return render_template("login.html", operadores=auth.listar_operadores())

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/api/sync")
    @login_required
    def api_sync():
        since = request.args.get("since", "")
        current = versao_atual()
        changed = not since or since != current
        payload = {"changed": changed, "version": current}
        if changed:
            payload["contagens"] = _contagens()
        return jsonify(payload)

    @app.route("/")
    @login_required
    def dashboard():
        u = _usuario_sessao()
        op = _escopo_operador()
        if u.get("is_gestor") and not op:
            painel = svc_mgestor.painel_gestor()
            return render_template(
                "dashboard_gestor.html",
                consolidado=painel["consolidado"],
                por_operador=painel["por_operador"],
                operadores=auth.listar_operadores(),
                agora=agora(),
                titulo_boas_vindas=u.get("titulo_boas_vindas"),
                subtitulo_boas_vindas=u.get("subtitulo_boas_vindas"),
            )
        m_trat = svc_tratativas.metricas(registrado_por=op)
        m_perf = svc_perf.metricas(registrado_por=op)
        m_vtrat = svc_vtrat.metricas(registrado_por=op)
        em_aberto = svc_tratativas.listar_em_aberto(registrado_por=op)
        perf_andamento = svc_perf.listar_em_andamento(registrado_por=op)
        return render_template(
            "dashboard.html",
            m_trat=m_trat,
            m_perf=m_perf,
            m_vtrat=m_vtrat,
            em_aberto=em_aberto,
            perf_andamento=perf_andamento,
            agora=agora(),
            titulo_boas_vindas=u.get("titulo_boas_vindas"),
            subtitulo_boas_vindas=u.get("subtitulo_boas_vindas"),
            operador_filtro=op,
        )

    # --- Vendas Performance ---
    def _dados_performance_form() -> dict:
        status = request.form.get("status_venda", "Em andamento")
        motivo = request.form.get("motivo_perda") or None
        if status != "Negócio perdido":
            motivo = None
        return {
            "pedido": request.form["pedido"],
            "valor": request.form["valor"],
            "status_venda": status,
            "previsao_data": request.form.get("previsao_data") or None,
            "cliente": request.form.get("cliente") or None,
            "vendedor": request.form.get("vendedor") or None,
            "motivo_perda": motivo or "concorrencia",
            "concorrencia": request.form.get("concorrencia") or None,
            "observacao": request.form.get("observacao") or None,
        }

    @app.route("/vendas-performance")
    @login_required
    def vendas_performance_lista():
        op = _escopo_operador()
        status = request.args.get("status") or None
        itens = svc_perf.listar(filtro_status=status, registrado_por=op)
        em_andamento = svc_perf.listar_em_andamento(registrado_por=op)
        return render_template(
            "vendas_performance.html",
            itens=itens,
            em_andamento=em_andamento,
            status_opts=config.STATUS_VENDA_PERFORMANCE,
            motivos_perda=config.MOTIVOS_PERDA,
            filtro_status=status,
            operador_filtro=op,
            operadores=auth.listar_operadores(),
            is_gestor=_usuario_sessao().get("is_gestor"),
        )

    @app.route("/vendas-performance/nova", methods=["POST"])
    @login_required
    def venda_performance_nova():
        dados = _dados_performance_form()
        ok, msg = validar_venda_performance(
            dados["status_venda"],
            dados.get("previsao_data"),
            dados.get("motivo_perda"),
            dados.get("concorrencia"),
        )
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("vendas_performance_lista"))
        dados["registrado_por"] = _registrado_por_atual()
        svc_perf.criar(dados)
        flash("Venda registrada no painel Performance.", "ok")
        return redirect(url_for("vendas_performance_lista"))

    @app.route("/vendas-performance/<int:vid>/editar", methods=["POST"])
    @login_required
    def venda_performance_editar(vid):
        dados = _dados_performance_form()
        ok, msg = validar_venda_performance(
            dados["status_venda"],
            dados.get("previsao_data"),
            dados.get("motivo_perda"),
            dados.get("concorrencia"),
        )
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("vendas_performance_lista"))
        svc_perf.atualizar(vid, dados)
        flash("Registro atualizado.", "ok")
        return redirect(url_for("vendas_performance_lista"))

    @app.route("/vendas-performance/<int:vid>/excluir", methods=["POST"])
    @login_required
    def venda_performance_excluir(vid):
        svc_perf.excluir(vid)
        flash("Registro removido.", "ok")
        return redirect(url_for("vendas_performance_lista"))

    # Redirects legados
    @app.route("/vendas")
    @app.route("/negocios")
    def redirect_antigos():
        return redirect(url_for("vendas_performance_lista"))

    # --- Tratativas ---
    def _dados_tratativa_form() -> dict:
        situacao = request.form["situacao"]
        codigo = (request.form.get("codigo_item") or "").strip() or None
        if situacao not in config.SITUACOES_COM_CODIGO_ITEM:
            codigo = None
        impacto = request.form.get("impacto_reais")
        return {
            "setor": request.form["setor"],
            "situacao": situacao,
            "tempo_solucao": request.form.get("tempo_solucao") or None,
            "impacto_reais": float(impacto) if impacto else None,
            "status": request.form["status"],
            "codigo_item": codigo,
            "numero_orcamento": (request.form.get("numero_orcamento") or "").strip()
            or None,
            "observacao": request.form.get("observacao") or None,
        }

    @app.route("/tratativas")
    @login_required
    def tratativas_lista():
        op = _escopo_operador()
        status = request.args.get("status") or None
        setor = request.args.get("setor") or None
        itens = svc_tratativas.listar(
            filtro_status=status, filtro_setor=setor, registrado_por=op
        )
        em_aberto = svc_tratativas.listar_em_aberto(registrado_por=op)
        resolvidas = svc_tratativas.listar(apenas_resolvidas=True, registrado_por=op)
        vendas_trat = {
            v["id_tratativa"]: v for v in svc_vtrat.listar(registrado_por=op)
        }
        ids_abertos = {t["id"] for t in em_aberto}
        return render_template(
            "tratativas.html",
            itens=itens,
            em_aberto=em_aberto,
            resolvidas=resolvidas,
            vendas_trat=vendas_trat,
            ids_abertos=ids_abertos,
            setores=config.SETORES,
            situacoes=config.SITUACOES,
            situacoes_codigo_item=config.SITUACOES_COM_CODIGO_ITEM,
            tempos=config.TEMPOS_SOLUCAO,
            status_opts=config.STATUS_TRATATIVA,
            status_resolvidos=config.STATUS_TRATATIVA_RESOLVIDA,
            filtro_status=status,
            filtro_setor=setor,
            operador_filtro=op,
            operadores=auth.listar_operadores(),
            is_gestor=_usuario_sessao().get("is_gestor"),
        )

    @app.route("/tratativas/nova", methods=["POST"])
    @login_required
    def tratativa_nova():
        dados = _dados_tratativa_form()
        ok, msg = validar_tratativa_situacao(dados["situacao"], dados.get("codigo_item"))
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("tratativas_lista"))
        dados["registrado_por"] = _registrado_por_atual()
        svc_tratativas.criar(dados)
        flash("Tratativa registrada com sucesso.", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/tratativas/<int:tid>/editar", methods=["POST"])
    @login_required
    def tratativa_editar(tid):
        dados = _dados_tratativa_form()
        ok, msg = validar_tratativa_situacao(dados["situacao"], dados.get("codigo_item"))
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("tratativas_lista"))
        svc_tratativas.atualizar(tid, dados)
        flash("Tratativa atualizada.", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/tratativas/<int:tid>/excluir", methods=["POST"])
    @login_required
    def tratativa_excluir(tid):
        svc_tratativas.excluir(tid)
        flash("Tratativa removida.", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/tratativas/<int:tid>/venda", methods=["POST"])
    @login_required
    def tratativa_registrar_venda(tid):
        trat = svc_tratativas.obter(tid)
        if not trat:
            flash("Tratativa não encontrada.", "erro")
            return redirect(url_for("tratativas_lista"))
        ok, msg = validar_venda_tratativa(tid, trat["status"])
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("tratativas_lista"))
        pedido = request.form.get("pedido") or trat.get("numero_orcamento") or f"TRAT-{tid}"
        svc_vtrat.criar(
            {
                "id_tratativa": tid,
                "pedido": pedido,
                "valor": request.form["valor"],
                "observacao": request.form.get("observacao"),
                "registrado_por": _registrado_por_atual(),
            },
            trat["status"],
        )
        flash("Venda da tratativa registrada (convertida).", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/exportar")
    @login_required
    def exportar():
        painel = svc_mgestor.painel_gestor()
        c = painel["consolidado"]
        return render_template(
            "exportar.html",
            m_trat=c["trat"],
            m_perf=c["perf"],
            m_vtrat=c["vtrat"],
            por_operador=painel["por_operador"],
        )

    @app.route("/exportar/excel")
    @login_required
    def exportar_excel():
        buffer, nome = svc_exportacao.gerar_excel()
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/backup", methods=["POST"])
    @login_required
    def backup():
        path_db = backup_database("manual")
        path_json = export_json_snapshot()
        if path_db:
            flash(f"Backup criado: {path_db.name} e {path_json.name}", "ok")
        else:
            flash(f"Snapshot JSON salvo: {path_json.name}", "ok")
        return redirect(url_for("dashboard"))

    @app.route("/api/metricas")
    @login_required
    def api_metricas():
        return jsonify(
            {
                "tratativas": svc_tratativas.metricas(),
                "performance": svc_perf.metricas(),
                "vendas_tratativa": svc_vtrat.metricas(),
            }
        )

    return app
