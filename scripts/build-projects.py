#!/usr/bin/env python3
"""Write public/projects/index.html from projects.json.

Adding a project is one entry in projects.json, then: python3 scripts/build-projects.py
The order in projects.json is the order on the page: strongest proof first.
Fields: name; story (one paragraph, at most 70 words: open with the problem, name the
option you rejected, end on one checkable fact); status (live | preview | building |
soon | retired); year; href (a path on this site when the project has earned its own
page, a full URL for its own site, or null when it isn't public yet); credit (optional,
a short plain label such as "Built at work", shown under the status; never a company name).
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATUSES = {"live": "Live", "preview": "Preview", "building": "Building", "soon": "Soon", "retired": "Retired"}
MAX_WORDS = 70
MAX_CREDIT_CHARS = 30
esc = html.escape

projects = json.loads((ROOT / "projects.json").read_text())
for p in projects:
    assert p["status"] in STATUSES, f"{p['name']}: unknown status {p['status']!r}"
    words = len(p.get("story", "").split())
    assert words, f"{p['name']}: needs a story"
    assert words <= MAX_WORDS, f"{p['name']}: story is {words} words, the cap is {MAX_WORDS}"
    credit = p.get("credit")
    assert credit is None or (isinstance(credit, str) and 0 < len(credit) <= MAX_CREDIT_CHARS), \
        f"{p['name']}: credit must be 1 to {MAX_CREDIT_CHARS} characters"


def link(p):
    href = p.get("href")
    if not href:
        return ""
    if href.startswith("http"):
        host = href.split("//", 1)[1].rstrip("/")
        return (f'<a class="go" href="{esc(href)}">{esc(host)}&nbsp;<span class="ar" aria-hidden="true">↗</span>'
                f'<span class="sr"> (opens its own site)</span></a>')
    return f'<a class="go" href="{esc(href)}">Read the page&nbsp;<span class="ar" aria-hidden="true">→</span></a>'


def row(p):
    credit = f'<span>{esc(p["credit"])}</span>' if p.get("credit") else ""
    return (f'<li><p class="meta"><span>{p["year"]}</span><span>{STATUSES[p["status"]]}</span>{credit}</p>'
            f'<div><h2>{esc(p["name"])}</h2><p class="story">{esc(p["story"])}</p>{link(p)}</div></li>')


template = (ROOT / "scripts" / "projects.template.html").read_text()
out = ROOT / "public" / "projects" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(template.replace("{{ROWS}}", "\n".join(row(p) for p in projects)))
print(f"Wrote {out.relative_to(ROOT)} with {len(projects)} projects")
