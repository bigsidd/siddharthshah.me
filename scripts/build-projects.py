#!/usr/bin/env python3
"""Write public/projects/index.html from projects.json.

Adding a project is one entry in projects.json, then: python3 scripts/build-projects.py
Fields: name, line, call (required: the decision that made it work), problem and result
(optional, shown on tap; leave result out rather than repeating the line), status
(live | preview | building | soon | retired), year, href (a path on this site, a full URL
for a project's own site, or null when it isn't public yet).
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ORDER = ["live", "preview", "building", "soon", "retired"]
LABEL = {"live": "Live", "preview": "Preview", "building": "Building", "soon": "Soon", "retired": "Retired"}
esc = html.escape

projects = json.loads((ROOT / "projects.json").read_text())
for p in projects:
    assert p["status"] in ORDER, f"{p['name']}: unknown status {p['status']!r}"
    assert p.get("call", "").strip(), f"{p['name']}: needs a call (the decision that made it work)"
projects.sort(key=lambda p: (ORDER.index(p["status"]), -int(p["year"])))


def link(p):
    href = p.get("href")
    if not href:
        return ""
    if href.startswith("http"):
        host = href.split("//", 1)[1].rstrip("/")
        return (f'<a class="go" href="{esc(href)}">{esc(host)} <span class="ar" aria-hidden="true">↗</span>'
                f'<span class="sr"> (opens its own site)</span></a>')
    return f'<a class="go" href="{esc(href)}">Read the page here <span class="ar" aria-hidden="true">→</span></a>'


def entry(p):
    more = [(k, p[k]) for k in ("problem", "result") if p.get(k)]
    details = ""
    if more:
        label = " and ".join(k.capitalize() if i == 0 else k for i, (k, _) in enumerate(more))
        rows = "".join(f'<div class="item"><dt>{k.capitalize()}</dt><dd>{esc(v)}</dd></div>' for k, v in more)
        details = (f'<details><summary><span class="mk" aria-hidden="true"></span>{label}</summary>'
                   f'<dl>{rows}</dl></details>')
    size = "big" if p["status"] == "live" else "small"
    return (f'<li class="p {size}">'
            f'<div class="hd"><h3>{esc(p["name"])}</h3><span class="yr">{p["year"]}</span></div>'
            f'<div class="tx"><p class="ln">{esc(p["line"])}</p>'
            f'<p class="call"><span class="lab">The call</span>{esc(p["call"])}</p>'
            f'{details}{link(p)}</div></li>')


groups, counts = [], []
for s in ORDER:
    items = [p for p in projects if p["status"] == s]
    if not items:
        continue
    counts.append(f'<a href="#{s}">{len(items)} {LABEL[s].lower()}</a>')
    groups.append(f'<section aria-labelledby="{s}"><h2 id="{s}">{LABEL[s]}</h2><ul>'
                  + "\n".join(entry(p) for p in items) + "</ul></section>")

template = (ROOT / "scripts" / "projects.template.html").read_text()
out = ROOT / "public" / "projects" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(template.replace("{{GROUPS}}", "\n".join(groups)).replace("{{COUNTS}}", " · ".join(counts)))
print(f"Wrote {out.relative_to(ROOT)} with {len(projects)} projects")
