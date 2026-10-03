"""
Build the static dashboard page (docs/index.html, served by GitHub Pages).

    python scripts/run_local.py
    python scripts/export_dashboard_data.py
    python scripts/build_dashboard.py
"""
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
tpl = open(os.path.join(ROOT, "dashboard", "template.html"), encoding="utf-8").read()
data = open(os.path.join(ROOT, "dashboard_data.json"), encoding="utf-8").read()
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '</head>\n<body style="margin:0">\n' + tpl.replace("__DATA__", data) + '\n</body>\n</html>\n')
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
print("docs/index.html written")
