import json
import os
import requests
import subprocess
import sys

FILE_PATH = "data/hackerone_data.json"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Credenciales de Telegram no encontradas en el entorno.")
        return
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
            print("✅ Notificación enviada a Telegram.")
        else:
            print(f"❌ Error de Telegram ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Error conectando con Telegram: {e}")

def get_real_data_commit(offset_index):
    """
    Busca el Hash del commit exacto donde realmente cambió hackerone_data.json,
    ignorando los commits de index.html creados por el bot.
    """
    try:
        res = subprocess.run(
            ["git", "log", f"-n", str(offset_index), "--format=%H", "--", FILE_PATH],
            capture_output=True, text=True, check=True
        )
        commits = [c.strip() for c in res.stdout.strip().split("\n") if c.strip()]
        if commits:
            # Retorna el commit más antiguo de la lista solicitada
            return commits[-1]
    except Exception as e:
        print(f"⚠️ Error consultando git log para {FILE_PATH}: {e}")
    return None

def get_git_json(commit_ref):
    try:
        res = subprocess.run(["git", "show", f"{commit_ref}:{FILE_PATH}"], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        print(f"⚠️ No se pudo leer {FILE_PATH} en la revisión {commit_ref}: {e}")
        return None

def extract_programs(json_data):
    programs = {}
    if not json_data or not isinstance(json_data, list):
        return programs

    for prog in json_data:
        if not isinstance(prog, dict):
            continue
        handle = prog.get("handle")
        if handle:
            targets = prog.get("targets", {}).get("in_scope", [])
            count = len(targets) if isinstance(targets, list) else 0
            programs[handle] = {
                "name": prog.get("name", handle),
                "handle": handle,
                "offers_bounties": prog.get("offers_bounties", False),
                "url": prog.get("url", f"https://hackerone.com/{handle}"),
                "targets_count": count
            }
    return programs

def main():
    # Si se pasa un argumento numérico (ej. 500) o un commit ref, lo usa; si no, analiza el cambio más reciente
    depth_arg = sys.argv[1] if len(sys.argv) > 1 else "1"

    if depth_arg.isdigit():
        target_ref = get_real_data_commit(int(depth_arg))
    else:
        target_ref = depth_arg

    if not target_ref:
        target_ref = "HEAD~1"

    print(f"🔍 Comparando cambios de datos reales en {FILE_PATH}:")
    print(f"   Commit base: {target_ref} ──> HEAD")

    new_data = get_git_json("HEAD")
    old_data = get_git_json(target_ref)

    if not new_data or not old_data:
        print("❌ No se pudieron obtener los datos de Git para realizar la comparación.")
        return

    old_progs = extract_programs(old_data)
    new_progs = extract_programs(new_data)

    print(f"   • Programas detectados en revisión antigua: {len(old_progs)}")
    print(f"   • Programas detectados en HEAD: {len(new_progs)}")

    new_handles = set(new_progs.keys()) - set(old_progs.keys())

    if not new_handles:
        print("[+] No hay programas nuevos entre estas dos revisiones de datos.")
        return

    print(f"🎉 ¡Se han detectado {len(new_handles)} programa(s) nuevo(s)!: {', '.join(new_handles)}")

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
