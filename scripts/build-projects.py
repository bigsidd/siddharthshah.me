#!/usr/bin/env python3
"""Write public/projects/index.html from projects.json.

Adding a project is one entry in projects.json, then: python3 scripts/build-projects.py
Fields: name, line, status (live | preview | building | soon | retired), year, href
(a path on this site, a full URL for a project's own site, or null when it isn't public yet).
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORDER = ["live", "preview", "building", "soon", "retired"]
LABEL = {"live": "Live", "preview": "Preview", "building": "Building", "soon": "Soon", "retired": "Retired"}

projects = json.loads((ROOT / "projects.json").read_text())
for p in projects:
    assert p["status"] in ORDER, f"{p['name']}: unknown status {p['status']!r}"
projects.sort(key=lambda p: (ORDER.index(p["status"]), -int(p["year"])))


def row(p):
    name, line = html.escape(p["name"]), html.escape(p["line"])
    status = f'<span class="st {p["status"]}">{LABEL[p["status"]]}</span>'
    year = f'<span class="yr">{p["year"]}</span>'
    href = p.get("href")
    if not href:
        return f'<li><div class="row"><b>{name}</b><span class="ln">{line}</span>{status}{year}<span class="ar"></span></div></li>'
    external = href.startswith("http")
    arrow = "↗" if external else "→"
    return (f'<li><a class="row" href="{html.escape(href)}"><b>{name}</b><span class="ln">{line}</span>{status}{year}'
            f'<span class="ar" aria-hidden="true">{arrow}</span>'
            f'{"<span class=sr>(opens its own site)</span>" if external else ""}</a></li>')


rows = "\n".join(row(p) for p in projects)
template = (ROOT / "scripts" / "projects.template.html").read_text()
out = ROOT / "public" / "projects" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(template.replace("{{ROWS}}", rows).replace("{{COUNT}}", str(len(projects))))
print(f"Wrote {out.relative_to(ROOT)} with {len(projects)} projects")
