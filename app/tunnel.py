"""Túnel HTTPS para acesso pelo celular (quando IP local não funciona)."""

import os
import re
import subprocess
import time

_processos: list[subprocess.Popen] = []


def _ngrok(port: int) -> str | None:
    token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if not token:
        return None
    try:
        from pyngrok import conf, ngrok

        conf.get_default().auth_token = token
        tunnel = ngrok.connect(port, bind_tls=True)
        return tunnel.public_url
    except Exception as exc:
        print(f"  Ngrok: {exc}")
        return None


def _cloudflared(port: int) -> str | None:
    try:
        proc = subprocess.Popen(
            [
                "cloudflared",
                "tunnel",
                "--url",
                f"http://127.0.0.1:{port}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        _processos.append(proc)
        deadline = time.time() + 30
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                time.sleep(0.2)
                continue
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                return match.group(0)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"  Cloudflared: {exc}")
        return None
    return None


def iniciar_tunel(port: int) -> str | None:
    """Tenta ngrok (com token) ou cloudflared (se instalado)."""
    url = _ngrok(port)
    if url:
        return url
    return _cloudflared(port)
