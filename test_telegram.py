import json
import os
import requests
import subprocess
import sys

FILE_PATH = "data/hackerone_data.json"

# Lee variables de entorno o valores para pruebas en local
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_telegram(msg):
    """Envía la alerta a Telegram o la imprime por consola si faltan credenciales."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n⚠️ [AVISO] Las variables de Telegram no están configuradas.")
        print("   Notificación simulada que se enviaría a Telegram:\n")
        print("--------------------------------------------------")
        print(msg)
        print("--------------------------------------------------\n")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"✅ Notificación enviada con éxito a Telegram.")
            return True
        else:
            print(f"❌ Error de Telegram API ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"❌ Error de red al conectar con Telegram: {e}")
        return False

def get_git_json(commit_ref):
    """Extrae y parsea el archivo JSON en una revisión específica de Git."""
    try:
        res = subprocess.run(
            ["git", "show", f"{commit_ref}:{FILE_PATH}"],
            capture_output=True, text=True, check=True
        )
        return json.loads(res.stdout)
    except subprocess.CalledProcessError:
        print(f"⚠️ No se pudo leer '{commit_ref}:{FILE_PATH}'. Puede que el commit no exista localmente.")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error de formato JSON en {commit_ref}: {e}")
        return None

def extract_programs_dict(json_data):
    """Convierte la lista del JSON en un diccionario mapeado por 'handle'."""
    if not json_data or not isinstance(json_data, list):
        return {}

    programs = {}
    for prog in json_data:
        if not isinstance(prog, dict):
            continue
        handle = prog.get("handle")
        if handle:
            targets_in_scope = prog.get("targets", {}).get("in_scope", [])
            in_scope_count = len(targets_in_scope) if isinstance(targets_in_scope, list) else 0

            programs[handle] = {
                "name": prog.get("name", handle),
                "handle": handle,
                "offers_bounties": bool(prog.get("offers_bounties", False)),
                "url": prog.get("url") or f"https://hackerone.com/{handle}",
                "targets_count": in_scope_count
            }
    return programs

def main():
    # Permite pasar el commit de comparación por argumento (por defecto HEAD~1)
    target_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"

    print("🔍 [1/3] Analizando repositorio Git...")
    print(f"   Punto de comparación: {target_ref} ──> HEAD")

    new_json = get_git_json("HEAD")
    old_json = get_git_json(target_ref)

    if not new_json:
        print("❌ Error crítico: No se pudo leer la versión actual (HEAD).")
        return

    # Si la referencia pedida falla (ej. HEAD~500 en repositorios con pocos commits), busca el más antiguo
    if not old_json:
        print("🔄 Buscando el commit base más antiguo disponible en tu historial local...")
        try:
            oldest_commit = subprocess.run(
                ["git", "rev-list", "--max-parents=0", "HEAD"],
                capture_output=True, text=True, check=True
            ).stdout.strip().split("\n")[-1]
            print(f"   Usando commit base: {oldest_commit}")
            old_json = get_git_json(oldest_commit)
        except Exception:
            pass

    if not old_json:
        print("❌ No se pudo obtener una versión anterior para realizar el diff.")
        return

    print("📊 [2/3] Mapeando programas...")
    old_progs = extract_programs_dict(old_json)
    new_progs = extract_programs_dict(new_json)

    print(f"   • Programas en {target_ref}: {len(old_progs)}")
    print(f"   • Programas en HEAD: {len(new_progs)}")

    # Cálculo de la diferencia de Handles
    new_handles = set(new_progs.keys()) - set(old_progs.keys())

    print("\n📢 [3/3] Resultados del análisis:")
    if not new_handles:
        print("ℹ️ No se detectó ningún programa nuevo entre ambas revisiones.")
        return

    print(f"🎉 ¡SE DETECTARON {len(new_handles)} PROGRAMA(S) NUEVO(S)!: {', '.join(new_handles)}\n")

    for handle in new_handles:
        p = new_progs[handle]
        bounty_status = "💰 *PAGA RECOMPENSAS (Bounty)*" if p["offers_bounties"] else "ℹ️ *PROGRAMA VDP (Sin Dinero)*"

        msg = (
            f"🚀 *¡NUEVO PROGRAMA PUBLICADO EN HACKERONE!*\n\n"
            f"*Nombre:* {p['name']}\n"
            f"*Handle:* `@{p['handle']}`\n"
            f"*Estado:* {bounty_status}\n"
            f"*Objetivos iniciales:* {p['targets_count']}\n\n"
            f"🔗 [Abrir en HackerOne]({p['url']})"
        )
        send_telegram(msg)

if __name__ == "__main__":
    main()
