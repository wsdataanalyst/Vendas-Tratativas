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
from app.services import negocios as svc_negocios
from app.services import tratativas as svc_tratativas
from app.services import vendas as svc_vendas
from app.utils.cache import get as cache_get
from app.utils.datetime_br import agora, formatar
from app.utils.realtime import versao_atual
from app.validators import validar_perda, validar_tratativa_situacao


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

    def _contagens():
        def factory():
            m_trat = svc_tratativas.metricas()
            m_vend = svc_vendas.metricas()
            m_neg = svc_negocios.metricas()
            return {
                "tratativas_abertas": m_trat.get("em_andamento", 0),
                "vendas_sem_conversao": m_vend.get("sem_conversao", 0),
                "negocios_acompanhamento": m_neg.get("em_acompanhamento", 0),
                "negocios_pendentes_vinculo": m_neg.get("perdidos_sem_vinculo", 0),
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
        return render_template("login.html", usuarios=auth.USUARIOS)

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
        m_trat = svc_tratativas.metricas()
        m_vendas = svc_vendas.metricas()
        m_neg = svc_negocios.metricas()
        em_aberto = svc_tratativas.listar_em_aberto()
        sem_conversao = svc_vendas.listar_sem_conversao()
        negocios_acomp = svc_negocios.listar_em_acompanhamento()
        u = session.get("usuario", {})
        return render_template(
            "dashboard.html",
            m_trat=m_trat,
            m_vendas=m_vendas,
            m_neg=m_neg,
            em_aberto=em_aberto,
            sem_conversao=sem_conversao,
            negocios_acomp=negocios_acomp,
            agora=agora(),
            titulo_boas_vindas=u.get("titulo_boas_vindas", "Bem-vinda, Mayara Barros!"),
            subtitulo_boas_vindas=u.get("subtitulo_boas_vindas", ""),
        )

    @app.route("/tratativas")
    @login_required
    def tratativas_lista():
        status = request.args.get("status") or None
        setor = request.args.get("setor") or None
        itens = svc_tratativas.listar(filtro_status=status, filtro_setor=setor)
        em_aberto = svc_tratativas.listar_em_aberto()
        ids_abertos = {t["id"] for t in em_aberto}
        return render_template(
            "tratativas.html",
            itens=itens,
            em_aberto=em_aberto,
            ids_abertos=ids_abertos,
            setores=config.SETORES,
            situacoes=config.SITUACOES,
            situacoes_codigo_item=config.SITUACOES_COM_CODIGO_ITEM,
            tempos=config.TEMPOS_SOLUCAO,
            status_opts=config.STATUS_TRATATIVA,
            filtro_status=status,
            filtro_setor=setor,
        )

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
            "observacao": request.form.get("observacao") or None,
        }

    @app.route("/tratativas/nova", methods=["POST"])
    @login_required
    def tratativa_nova():
        dados = _dados_tratativa_form()
        ok, msg = validar_tratativa_situacao(dados["situacao"], dados.get("codigo_item"))
        if not ok:
            flash(msg, "erro")
            return redirect(url_for("tratativas_lista"))
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

    def _dados_venda_form():
        convertido = request.form.get("convertido") == "on"
        motivo = request.form.get("motivo_perda") or None
        if convertido:
            motivo = None
        elif not motivo:
            motivo = "tratativa"
        return {
            "pedido": request.form["pedido"],
            "valor": request.form["valor"],
            "convertido": convertido,
            "motivo_perda": motivo,
            "id_perda": int(request.form["id_perda"])
            if request.form.get("id_perda")
            else None,
            "concorrencia": request.form.get("concorrencia") or None,
            "observacao": request.form.get("observacao") or None,
        }

    def _validar_venda_form(dados: dict) -> bool:
        ok, msg = validar_perda(
            convertido=dados["convertido"],
            motivo_perda=dados.get("motivo_perda"),
            id_tratativa=dados.get("id_perda"),
            concorrencia=dados.get("concorrencia"),
        )
        if not ok:
            flash(msg, "erro")
        return ok

    @app.route("/vendas")
    @login_required
    def vendas_lista():
        itens = svc_vendas.listar()
        sem_conversao = svc_vendas.listar_sem_conversao()
        tratativas = svc_tratativas.listar()
        em_aberto = svc_tratativas.listar_em_aberto()
        return render_template(
            "vendas.html",
            itens=itens,
            sem_conversao=sem_conversao,
            tratativas=tratativas,
            tratativas_abertas=em_aberto,
            motivos_perda=config.MOTIVOS_PERDA,
        )

    @app.route("/vendas/nova", methods=["POST"])
    @login_required
    def venda_nova():
        dados = _dados_venda_form()
        if not _validar_venda_form(dados):
            return redirect(url_for("vendas_lista"))
        svc_vendas.criar(dados)
        flash("Venda registrada.", "ok")
        return redirect(url_for("vendas_lista"))

    @app.route("/vendas/<int:vid>/editar", methods=["POST"])
    @login_required
    def venda_editar(vid):
        dados = _dados_venda_form()
        if not _validar_venda_form(dados):
            return redirect(url_for("vendas_lista"))
        svc_vendas.atualizar(vid, dados)
        flash("Venda atualizada.", "ok")
        return redirect(url_for("vendas_lista"))

    @app.route("/vendas/<int:vid>/excluir", methods=["POST"])
    @login_required
    def venda_excluir(vid):
        svc_vendas.excluir(vid)
        flash("Venda removida.", "ok")
        return redirect(url_for("vendas_lista"))

    def _dados_negocio_form():
        status = request.form.get("status", "Em acompanhamento")
        motivo = request.form.get("motivo_perda") or None
        if status != "Perdido":
            motivo = None
        return {
            "referencia": request.form["referencia"],
            "cliente": request.form.get("cliente") or None,
            "vendedor": request.form.get("vendedor") or None,
            "valor": request.form["valor"],
            "status": status,
            "motivo_perda": motivo,
            "id_tratativa": int(request.form["id_tratativa"])
            if request.form.get("id_tratativa")
            else None,
            "concorrencia": request.form.get("concorrencia") or None,
            "observacao": request.form.get("observacao") or None,
        }

    def _validar_negocio_form(dados: dict) -> bool:
        ok, msg = validar_perda(
            status=dados["status"],
            motivo_perda=dados.get("motivo_perda"),
            id_tratativa=dados.get("id_tratativa"),
            concorrencia=dados.get("concorrencia"),
        )
        if not ok:
            flash(msg, "erro")
        return ok

    @app.route("/negocios")
    @login_required
    def negocios_lista():
        status = request.args.get("status") or None
        itens = svc_negocios.listar(filtro_status=status)
        em_acompanhamento = svc_negocios.listar_em_acompanhamento()
        tratativas = svc_tratativas.listar()
        em_aberto = svc_tratativas.listar_em_aberto()
        return render_template(
            "negocios.html",
            itens=itens,
            em_acompanhamento=em_acompanhamento,
            tratativas=tratativas,
            tratativas_abertas=em_aberto,
            status_opts=config.STATUS_NEGOCIO,
            motivos_perda=config.MOTIVOS_PERDA,
            filtro_status=status,
        )

    @app.route("/negocios/nova", methods=["POST"])
    @login_required
    def negocio_nova():
        dados = _dados_negocio_form()
        if not _validar_negocio_form(dados):
            return redirect(url_for("negocios_lista"))
        svc_negocios.criar(dados)
        flash("Negócio registrado.", "ok")
        return redirect(url_for("negocios_lista"))

    @app.route("/negocios/<int:nid>/editar", methods=["POST"])
    @login_required
    def negocio_editar(nid):
        dados = _dados_negocio_form()
        if not _validar_negocio_form(dados):
            return redirect(url_for("negocios_lista"))
        svc_negocios.atualizar(nid, dados)
        flash("Negócio atualizado.", "ok")
        return redirect(url_for("negocios_lista"))

    @app.route("/negocios/<int:nid>/excluir", methods=["POST"])
    @login_required
    def negocio_excluir(nid):
        svc_negocios.excluir(nid)
        flash("Negócio removido.", "ok")
        return redirect(url_for("negocios_lista"))

    @app.route("/exportar")
    @login_required
    def exportar():
        m_trat = svc_tratativas.metricas()
        m_vendas = svc_vendas.metricas()
        m_neg = svc_negocios.metricas()
        return render_template(
            "exportar.html",
            m_trat=m_trat,
            m_vendas=m_vendas,
            m_neg=m_neg,
            total_tratativas=m_trat["total"],
            total_vendas=m_vendas["total"],
            total_negocios=m_neg["total"],
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
                "vendas": svc_vendas.metricas(),
                "negocios": svc_negocios.metricas(),
            }
        )

    return app
