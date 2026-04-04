"""
Obtiene el access token de Shopify via OAuth — PRAIE
Uso: python tools/obtener_token_shopify.py <client_secret>
"""

import hashlib
import hmac
import os
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
from dotenv import load_dotenv, set_key

load_dotenv()

SHOP          = os.getenv("SHOPIFY_STORE_URL", "").replace("https://", "").rstrip("/")
CLIENT_ID     = "970cf773faf187002e1d4ccdc4617d42"
CLIENT_SECRET = sys.argv[1] if len(sys.argv) > 1 else ""
SCOPES        = "read_checkouts,read_orders,read_customers,read_all_orders"
REDIRECT_URI  = "http://localhost:3000/callback"
PORT          = 3000
STATE         = secrets.token_hex(16)

result = {"token": None, "error": None}
done   = threading.Event()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"  [servidor] {format % args}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        print(f"\n  Callback recibido: {self.path[:80]}")

        if parsed.path != "/callback":
            self._ok("ignorado")
            return

        if params.get("state") != STATE:
            result["error"] = "State inválido"
            self._ok("Error: state inválido")
            done.set()
            return

        code = params.get("code")
        shop = params.get("shop", SHOP)

        if not code:
            result["error"] = "Sin código de autorización"
            self._ok("Error: sin código")
            done.set()
            return

        print(f"  Intercambiando código por token...")
        try:
            r = httpx.post(
                f"https://{shop}/admin/oauth/access_token",
                json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code},
                timeout=15,
            )
            if r.status_code == 200:
                result["token"] = r.json().get("access_token", "")
                result["shop"]  = shop
                self._ok("Token obtenido. Puedes cerrar esta ventana.")
            else:
                result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"
                self._ok(f"Error: {r.status_code}")
        except Exception as e:
            result["error"] = str(e)
            self._ok("Error de conexión")

        done.set()

    def _ok(self, msg):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode())


def main():
    if not CLIENT_SECRET:
        print("Uso: python tools/obtener_token_shopify.py <client_secret>")
        sys.exit(1)

    if not SHOP:
        print("Falta SHOPIFY_STORE_URL en .env")
        sys.exit(1)

    auth_url = (
        f"https://{SHOP}/admin/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&scope={SCOPES}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&state={STATE}"
    )

    # Verificar que el puerto esté libre
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", PORT)) == 0:
            print(f"ERROR: Puerto {PORT} ya está en uso. Cierra el proceso que lo ocupa.")
            sys.exit(1)

    print()
    print("=" * 60)
    print("  PRAIE — Obtener Token Shopify")
    print("=" * 60)
    print(f"\n  Tienda: {SHOP}")
    print(f"\n  Servidor escuchando en puerto {PORT}...")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()

    print(f"\n  Abre esta URL en tu navegador y aprueba la app:")
    print(f"\n  {auth_url}\n")
    print(f"  Esperando respuesta de Shopify (5 minutos)...")

    # Intentar abrir el navegador
    try:
        import webbrowser
        webbrowser.open(auth_url)
    except Exception:
        pass

    done.wait(timeout=300)
    server.shutdown()

    if not done.is_set():
        print("\n  Timeout — no se recibió respuesta en 5 minutos")
        print("  Asegúrate de abrir la URL de arriba y aprobar la app.")
        return

    if result.get("error"):
        print(f"\n  Error: {result['error']}")
        return

    token = result["token"]
    shop  = result.get("shop", SHOP)

    print(f"\n  Token: {token}")

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    set_key(env_path, "SHOPIFY_ACCESS_TOKEN", token)
    set_key(env_path, "SHOPIFY_STORE_URL", shop)

    print(f"\n  Guardado en .env")
    print(f"  Ahora corre: python tools/ver_carritos.py\n")


if __name__ == "__main__":
    main()
