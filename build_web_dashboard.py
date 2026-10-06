import json
import subprocess
import sys

FILE_PATH = "data/hackerone_data.json"

def get_git_json(commit_ref):
    try:
        res = subprocess.run(["git", "show", f"{commit_ref}:{FILE_PATH}"], capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception:
        return None

def extract_bounty_web_assets(data):
    assets = {}
    if not data:
        return assets
    for prog in data:
        handle = prog.get("handle")
        name = prog.get("name")
        for target in prog.get("targets", {}).get("in_scope", []):
            if target.get("eligible_for_bounty") and target.get("asset_type") in ["URL", "WILDCARD", "CIDR", "DOMAIN", "OTHER"]:
                asset = target.get("asset_identifier", "").strip()
                if asset:
                    assets[(handle, asset)] = {
                        "program": name,
                        "handle": handle,
                        "asset": asset,
                        "type": target.get("asset_type"),
                        "severity": target.get("max_severity", "N/A"),
                        "url": f"https://hackerone.com/{handle}"
                    }
    return assets

def main():
    new_data = get_git_json("HEAD") or []
    # 168 commits equivale a 7 días exactos en este repositorio
    old_data = get_git_json("HEAD~168") or get_git_json("HEAD~50") or []

    old_assets = extract_bounty_web_assets(old_data)
    new_assets = extract_bounty_web_assets(new_data)

    added_keys = set(new_assets.keys()) - set(old_assets.keys())

    showing_new = True
    display_keys = list(added_keys)

    # Si no hay dominios nuevos en los últimos 7 días, muestra los activos con bounty vigentes
    if not display_keys:
        showing_new = False
        display_keys = list(new_assets.keys())[:50]

    title_text = "🎯 Nuevos Activos con Bounty (Últimos 7 días)" if showing_new else "📋 Targets con Bounty Activos en HackerOne"
    subtitle_text = f"Nuevos añadidos esta semana: {len(added_keys)}" if showing_new else "No se añadieron subdominios nuevos en los últimos 7 días. Mostrando activos principales con recompensa:"

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>H1 Bounty Targets - Móvil</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 15px; margin: 0; }}
        h1 {{ color: #58a6ff; font-size: 1.3rem; margin-bottom: 5px; }}
        .subtitle {{ font-size: 0.85rem; color: #8b949e; margin-bottom: 15px; background: #161b22; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
        .asset {{ font-family: monospace; color: #7ee787; font-size: 1rem; word-break: break-all; font-weight: bold; }}
        .meta {{ font-size: 0.85rem; color: #8b949e; margin-top: 6px; }}
        .badge {{ display: inline-block; background: #238636; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }}
        a {{ color: #58a6ff; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 8px; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>{title_text}</h1>
    <div class="subtitle">{subtitle_text}</div>
"""

    for key in display_keys:
        item = new_assets[key]
        html_content += f"""
    <div class="card">
        <div class="asset">{item['asset']}</div>
        <div class="meta">Programa: <strong>{item['program']}</strong> (@{item['handle']})</div>
        <div style="margin-top:5px;">
            <span class="badge">{item['type']}</span>
            <span style="font-size:0.8rem; color:#8b949e; margin-left:8px;">Max: {item['severity']}</span>
        </div>
        <a href="{item['url']}" target="_blank">Ver Programa en HackerOne &rarr;</a>
    </div>"""

    html_content += "\n</body>\n</html>"

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
