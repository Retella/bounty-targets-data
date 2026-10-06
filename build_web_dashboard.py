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
    old_data = get_git_json("HEAD@{7.days.ago}") or get_git_json("HEAD~50") or []
    new_data = get_git_json("HEAD") or []

    old_assets = extract_bounty_web_assets(old_data)
    new_assets = extract_bounty_web_assets(new_data)

    added_keys = set(new_assets.keys()) - set(old_assets.keys())

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>H1 Bounty Targets - Móvil</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 15px; margin: 0; }}
        h1 {{ color: #58a6ff; font-size: 1.3rem; margin-bottom: 5px; }}
        .subtitle {{ font-size: 0.85rem; color: #8b949e; margin-bottom: 15px; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
        .asset {{ font-family: monospace; color: #7ee787; font-size: 1rem; word-break: break-all; font-weight: bold; }}
        .meta {{ font-size: 0.85rem; color: #8b949e; margin-top: 6px; }}
        .badge {{ display: inline-block; background: #238636; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }}
        a {{ color: #58a6ff; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 8px; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>🎯 Nuevos Activos Web con Bounty</h1>
    <div class="subtitle">Añadidos en los últimos 7 días | Total: {len(added_keys)}</div>
"""

    for key in added_keys:
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
