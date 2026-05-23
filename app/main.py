import functools
from datetime import datetime

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
from app.services import tratativas as svc_tratativas
from app.services import vendas as svc_vendas


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = config.SECRET_KEY
    if config.IS_CLOUD:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True

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

        m_trat = svc_tratativas.metricas() if session.get("autenticado") else {}
        m_vendas = svc_vendas.metricas() if session.get("autenticado") else {}
        return {
            "config": config,
            "moeda": moeda,
            "is_cloud": config.IS_CLOUD,
            "usuario": session.get("usuario"),
            "contagens": {
                "tratativas_abertas": m_trat.get("em_andamento", 0),
                "vendas_sem_conversao": m_vendas.get("sem_conversao", 0),
            },
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
        return jsonify({"status": "ok", "database": db}), 200

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("autenticado"):
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            usuario_id = request.form.get("usuario", "").strip()
            senha = request.form.get("senha", "")
            dados = auth.autenticar(usuario_id, senha)
            if dados:
                session["autenticado"] = True
                session["usuario"] = dados
                return redirect(url_for("dashboard"))
            flash("Usuário ou senha incorretos.", "erro")
        return render_template("login.html", usuarios=auth.USUARIOS)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        m_trat = svc_tratativas.metricas()
        m_vendas = svc_vendas.metricas()
        em_aberto = svc_tratativas.listar_em_aberto()
        sem_conversao = svc_vendas.listar_sem_conversao()
        u = session.get("usuario", {})
        return render_template(
            "dashboard.html",
            m_trat=m_trat,
            m_vendas=m_vendas,
            em_aberto=em_aberto,
            sem_conversao=sem_conversao,
            agora=datetime.now(),
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
            tempos=config.TEMPOS_SOLUCAO,
            status_opts=config.STATUS_TRATATIVA,
            filtro_status=status,
            filtro_setor=setor,
        )

    @app.route("/tratativas/nova", methods=["POST"])
    @login_required
    def tratativa_nova():
        impacto = request.form.get("impacto_reais")
        svc_tratativas.criar(
            {
                "setor": request.form["setor"],
                "situacao": request.form["situacao"],
                "tempo_solucao": request.form.get("tempo_solucao") or None,
                "impacto_reais": float(impacto) if impacto else None,
                "status": request.form["status"],
                "observacao": request.form.get("observacao") or None,
            }
        )
        flash("Tratativa registrada com sucesso.", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/tratativas/<int:tid>/editar", methods=["POST"])
    @login_required
    def tratativa_editar(tid):
        impacto = request.form.get("impacto_reais")
        svc_tratativas.atualizar(
            tid,
            {
                "setor": request.form["setor"],
                "situacao": request.form["situacao"],
                "tempo_solucao": request.form.get("tempo_solucao") or None,
                "impacto_reais": float(impacto) if impacto else None,
                "status": request.form["status"],
                "observacao": request.form.get("observacao") or None,
            },
        )
        flash("Tratativa atualizada.", "ok")
        return redirect(url_for("tratativas_lista"))

    @app.route("/tratativas/<int:tid>/excluir", methods=["POST"])
    @login_required
    def tratativa_excluir(tid):
        svc_tratativas.excluir(tid)
        flash("Tratativa removida.", "ok")
        return redirect(url_for("tratativas_lista"))

    def _validar_venda_perdida(convertido: bool, id_perda: str | None) -> bool:
        if convertido:
            return True
        if not id_perda:
            flash(
                "Venda sem conversão deve vincular o ID da tratativa — "
                "o impacto financeiro vem sempre do problema registrado.",
                "erro",
            )
            return False
        return True

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
        )

    @app.route("/vendas/nova", methods=["POST"])
    @login_required
    def venda_nova():
        convertido = request.form.get("convertido") == "on"
        id_perda = request.form.get("id_perda")
        if not _validar_venda_perdida(convertido, id_perda):
            return redirect(url_for("vendas_lista"))
        svc_vendas.criar(
            {
                "pedido": request.form["pedido"],
                "valor": request.form["valor"],
                "convertido": convertido,
                "id_perda": int(id_perda) if id_perda else None,
                "observacao": request.form.get("observacao") or None,
            }
        )
        flash("Venda registrada.", "ok")
        return redirect(url_for("vendas_lista"))

    @app.route("/vendas/<int:vid>/editar", methods=["POST"])
    @login_required
    def venda_editar(vid):
        convertido = request.form.get("convertido") == "on"
        id_perda = request.form.get("id_perda")
        if not _validar_venda_perdida(convertido, id_perda):
            return redirect(url_for("vendas_lista"))
        svc_vendas.atualizar(
            vid,
            {
                "pedido": request.form["pedido"],
                "valor": request.form["valor"],
                "convertido": convertido,
                "id_perda": int(id_perda) if id_perda else None,
                "observacao": request.form.get("observacao") or None,
            },
        )
        flash("Venda atualizada.", "ok")
        return redirect(url_for("vendas_lista"))

    @app.route("/vendas/<int:vid>/excluir", methods=["POST"])
    @login_required
    def venda_excluir(vid):
        svc_vendas.excluir(vid)
        flash("Venda removida.", "ok")
        return redirect(url_for("vendas_lista"))

    @app.route("/exportar")
    @login_required
    def exportar():
        m_trat = svc_tratativas.metricas()
        m_vendas = svc_vendas.metricas()
        return render_template(
            "exportar.html",
            m_trat=m_trat,
            m_vendas=m_vendas,
            total_tratativas=m_trat["total"],
            total_vendas=m_vendas["total"],
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
        flash(f"Backup criado: {path_db.name} e {path_json.name}", "ok")
        return redirect(url_for("dashboard"))

    @app.route("/api/metricas")
    @login_required
    def api_metricas():
        return jsonify(
            {
                "tratativas": svc_tratativas.metricas(),
                "vendas": svc_vendas.metricas(),
            }
        )

    return app
