import json
import subprocess
import sys
from collections import defaultdict

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
    old_data = get_git_json("HEAD~168") or get_git_json("HEAD~50") or []

    old_assets = extract_bounty_web_assets(old_data)
    new_assets = extract_bounty_web_assets(new_data)

    added_keys = set(new_assets.keys()) - set(old_assets.keys())

    # Agrupar activos por programa (handle)
    grouped = defaultdict(list)
    for key in added_keys:
        item = new_assets[key]
        grouped[item['handle']].append(item)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>H1 Scope Updates - Móvil</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 15px; margin: 0; }}
        h1 {{ color: #58a6ff; font-size: 1.3rem; margin-bottom: 5px; }}
        .subtitle {{ font-size: 0.85rem; color: #8b949e; margin-bottom: 15px; background: #161b22; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; margin-bottom: 14px; }}
        .prog-title {{ font-size: 1.1rem; color: #f0f6fc; font-weight: bold; margin-bottom: 6px; }}
        .prog-handle {{ color: #8b949e; font-size: 0.9rem; font-weight: normal; }}
        .badge {{ display: inline-block; background: #238636; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-left: 6px; }}
        .asset-list {{ margin: 10px 0; padding-left: 0; }}
        .asset-item {{ font-family: monospace; color: #7ee787; font-size: 0.95rem; word-break: break-all; padding: 4px 0; border-bottom: 1px dashed #21262d; }}
        .asset-item:last-child {{ border-bottom: none; }}
        .type-tag {{ font-size: 0.75rem; color: #8b949e; background: #21262d; padding: 1px 5px; border-radius: 3px; font-family: sans-serif; margin-left: 5px; }}
        a {{ color: #58a6ff; text-decoration: none; font-weight: bold; display: inline-block; margin-top: 8px; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>🎯 Programas que Actualizaron Scope (Últimos 7 días)</h1>
    <div class="subtitle">Programas actualizados: {len(grouped)} | Total nuevos activos: {len(added_keys)}</div>
"""

    if not grouped:
        html_content += '<div class="card"><p style="margin:0; color:#8b949e;">No se añadieron subdominios/activos nuevos en los últimos 7 días.</p></div>'
    else:
        for handle, items in grouped.items():
            prog_name = items[0]['program']
            prog_url = items[0]['url']
            html_content += f"""
    <div class="card">
        <div class="prog-title">{prog_name} <span class="prog-handle">(@{handle})</span> <span class="badge">+{len(items)} activos</span></div>
        <div class="asset-list">"""
            for item in items:
                html_content += f"""
            <div class="asset-item">• {item['asset']} <span class="type-tag">{item['type']}</span></div>"""
            html_content += f"""
        </div>
        <a href="{prog_url}" target="_blank">Ver Programa en HackerOne &rarr;</a>
    </div>"""

    html_content += "\n</body>\n</html>"

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
