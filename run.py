"""
Vendas & Tratativas — PC, rede Wi-Fi ou túnel para celular.
"""
import os

from app.config import HOST, PORT
from app.main import create_app
from app.network import obter_ips_rede_local

USAR_TUNEL = os.getenv("USAR_TUNEL", "0").strip() in ("1", "true", "sim", "yes")


if __name__ == "__main__":
    app = create_app()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def sem_cache_html(response):
        if response.content_type and "text/html" in response.content_type:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    print("\n  Vendas & Tratativas")
    print(f"  Neste PC:  http://127.0.0.1:{PORT}")

    if USAR_TUNEL:
        from app.tunnel import iniciar_tunel

        print("\n  Abrindo link para celular (tunel)...")
        url_tunel = iniciar_tunel(PORT)
        if url_tunel:
            print("\n  ==========================================")
            print(f"  CELULAR — use este link (copie e cole):")
            print(f"  {url_tunel}")
            print("  ==========================================")
            print("  Funciona em qualquer rede (4G, Wi-Fi, etc.)")
            print("  Mantenha o PC ligado e esta janela aberta.\n")
        else:
            print("\n  Tunel nao iniciou.")
            print("  1) Crie conta gratis em https://ngrok.com")
            print("  2) Copie o token em https://dashboard.ngrok.com/get-started/your-authtoken")
            print("  3) Cole no arquivo .env como NGROK_AUTHTOKEN=seu_token")
            print("  4) Rode iniciar-celular.bat de novo\n")
    else:
        ips = obter_ips_rede_local()
        if ips:
            print("  Wi-Fi (mesma rede do PC):")
            for ip in ips:
                print(f"    http://{ip}:{PORT}")
        print("\n  Wi-Fi nao funciona? Use: iniciar-celular.bat\n")

    print("  Mayara — senha: mayara | Gestor Willame — senha: 161217")
    print(f"  Dados em: data/vendas_tratativas.db\n")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
