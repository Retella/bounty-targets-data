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
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    })

def get_git_json(commit_ref):
    try:
        res = subprocess.run(["git", "show", f"{commit_ref}:{FILE_PATH}"], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        sys.exit(1)

def extract_programs(json_data):
    programs = {}
    for prog in json_data:
        handle = prog.get("handle")
        if handle:
            programs[handle] = {
                "name": prog.get("name"),
                "handle": handle,
                "offers_bounties": prog.get("offers_bounties", False),
                "url": prog.get("url", f"https://hackerone.com/{handle}"),
                "targets_count": len(prog.get("targets", {}).get("in_scope", []))
            }
    return programs

def main():
    old_progs = extract_programs(get_git_json("HEAD~1"))
    new_progs = extract_programs(get_git_json("HEAD"))

    new_handles = set(new_progs.keys()) - set(old_progs.keys())

    if not new_handles:
        print("[+] No hay programas nuevos en esta actualización.")
        send_telegram("Holaaaa esto es una pruebecilla")
        return

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
