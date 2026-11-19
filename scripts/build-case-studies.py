#!/usr/bin/env python3
"""Write public/projects/<slug>/index.html for every case study in case-studies/.

    python3 scripts/build-case-studies.py

Each case study is a folder, case-studies/<slug>/, holding page.json and its screenshots.
page.json fields: title (the project's name, exactly as in projects.json); headline (says
what was built); description (one sentence for search and link previews); year; label
(optional, shown before the year); blocks, in reading order, each either
{"p": "paragraph"}, {"img": "file.png", "alt": "what it shows", "caption": "optional"}, or
{"links": [{"text": "link text", "href": "https://..."}]} for a short row of outbound links.

The build enforces: at most 300 words across headline, paragraphs, captions and link text;
every image exists, is a PNG and has alt text; every link is https and has text; and the
project's projects.json entry links to /projects/<slug>/. Images are copied next to the page with their real width and height.
"""
import html
import json
import pathlib
import shutil
import struct

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "case-studies"
MAX_WORDS = 300
esc = html.escape


def png_size(path):
    with path.open("rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name}: screenshots must be PNG"
    return struct.unpack(">II", head[16:24])


def words(text):
    return len(text.split())


projects = {p["name"]: p for p in json.loads((ROOT / "projects.json").read_text())}
template = (ROOT / "scripts" / "case-study.template.html").read_text()
built = 0
for folder in sorted(p for p in SRC.glob("*") if p.is_dir()):
    slug = folder.name
    page = json.loads((folder / "page.json").read_text())
    href = f"/projects/{slug}/"
    entry = projects.get(page["title"])
    assert entry, f"{slug}: no projects.json entry named {page['title']!r}"
    assert entry.get("href") == href, f"{slug}: its projects.json href should be {href}"

    out_dir = ROOT / "public" / "projects" / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    count = words(page["headline"])
    blocks = []
    for b in page["blocks"]:
        if "p" in b:
            count += words(b["p"])
            blocks.append(f"<p>{esc(b['p'])}</p>")
            continue
        if "links" in b:
            items = []
            for link in b["links"]:
                text, href = link.get("text", "").strip(), link.get("href", "").strip()
                assert text, f"{slug}: a link needs text"
                assert href.startswith("https://"), f"{slug}: link {text!r} must be https"
                count += words(text)
                items.append(f'<a href="{esc(href)}">{esc(text)}&nbsp;<span class="ar" aria-hidden="true">↗</span></a>')
            blocks.append(f'<p class="links">{"".join(items)}</p>')
            continue
        img = folder / b["img"]
        assert img.is_file(), f"{slug}: missing image {b['img']}"
        assert b.get("alt", "").strip(), f"{slug}: {b['img']} needs alt text"
        w, h = png_size(img)
        shutil.copy2(img, out_dir / img.name)
        cap = b.get("caption", "")
        count += words(cap)
        blocks.append(
            f'<figure><a href="{esc(img.name)}"><img src="{esc(img.name)}" alt="{esc(b["alt"])}" width="{w}" height="{h}" loading="lazy" decoding="async"></a>'
            + (f"<figcaption>{esc(cap)}</figcaption>" if cap else "") + "</figure>")
    assert count <= MAX_WORDS, f"{slug}: {count} words, the cap is {MAX_WORDS}"

    meta = "".join(f"<span>{esc(str(x))}</span>" for x in (page.get("label"), page["year"]) if x)
    out = (template.replace("{{SLUG}}", esc(slug)).replace("{{TITLE}}", esc(page["title"]))
           .replace("{{DESCRIPTION}}", esc(page["description"])).replace("{{META}}", meta)
           .replace("{{HEADLINE}}", esc(page["headline"])).replace("{{BLOCKS}}", "\n".join(blocks)))
    (out_dir / "index.html").write_text(out)
    built += 1
    print(f"Wrote public/projects/{slug}/index.html ({count} words)")
print(f"{built} case stud{'y' if built == 1 else 'ies'}")
