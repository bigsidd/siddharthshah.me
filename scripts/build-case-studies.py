#!/usr/bin/env python3
"""Write public/projects/<slug>/index.html for every case study in case-studies/.

    python3 scripts/build-case-studies.py

Each case study is a folder, case-studies/<slug>/, holding page.json and its PNG screenshots.
Every page has the same shape. The head fits inside the first screen at 390 and 1280px:
headline, one sentence on what was built, a facts strip, the outcome and the hero image. Below
it come the story, "The calls", secondary images and optional links.

page.json fields:
  title        the project's name, exactly as in projects.json
  headline     says what was built
  summary      one sentence: what it is and what it did
  description  one sentence for search and link previews
  year
  updated      YYYY-MM-DD, the page's sitemap lastmod
  at_work      true for work projects: shows "Built at work" and links to /resume/, which
               names the employer, so the page never has to
  label        optional, shown before the year when at_work is not set
  facts        exactly three [label, value] pairs, e.g. Role, Built with, Period
  outcome      one or two sentences: what happened because of it
  hero         {"img", "alt", "ratio": "16/10", "caption" (optional)}
  story        list of short paragraphs
  calls        list of {"call": "short name", "why": "one or two sentences"}
  gallery      optional {"layout": "pair" | "rail", "images": [{"img", "alt", "ratio", "caption"}]}
               pair takes exactly two images
  links        optional [{"text", "href": "https://..."}]

Every image sits in a fixed-ratio slot set by its "ratio", so a better screenshot drops in
without moving the layout; the image is scaled to fit, never cropped.

The build enforces: at most 300 words across all visible text (alt text excluded); every image
exists, is a PNG and has alt text; ratios look like "16/10"; links are https; and the project's
projects.json entry links to /projects/<slug>/. Images are copied next to the page, and
public/sitemap.xml gets one entry per case study, with "updated" as its lastmod.
"""
import html
import json
import pathlib
import re
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


def words(*texts):
    return sum(len(t.split()) for t in texts if t)


projects = {p["name"]: p for p in json.loads((ROOT / "projects.json").read_text())}
template = (ROOT / "scripts" / "case-study.template.html").read_text()
built = 0
lastmods = {}
for folder in sorted(p for p in SRC.glob("*") if p.is_dir()):
    slug = folder.name
    page = json.loads((folder / "page.json").read_text())
    href = f"/projects/{slug}/"
    entry = projects.get(page["title"])
    assert entry, f"{slug}: no projects.json entry named {page['title']!r}"
    assert entry.get("href") == href, f"{slug}: its projects.json href should be {href}"
    for field in ("headline", "summary", "description", "year", "updated", "facts", "outcome", "hero", "story", "calls"):
        assert page.get(field), f"{slug}: page.json needs {field}"

    out_dir = ROOT / "public" / "projects" / slug
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    def image(b, eager=False):
        img = folder / b["img"]
        assert img.is_file(), f"{slug}: missing image {b['img']}"
        assert b.get("alt", "").strip(), f"{slug}: {b['img']} needs alt text"
        ratio = b.get("ratio", "")
        assert re.fullmatch(r"\d+(\.\d+)?/\d+(\.\d+)?", ratio), f"{slug}: {b['img']} needs a ratio like 16/10"
        w, h = png_size(img)
        shutil.copy2(img, out_dir / img.name)
        load = 'fetchpriority="high"' if eager else 'loading="lazy"'
        cap = f"<figcaption>{esc(b['caption'])}</figcaption>" if b.get("caption") else ""
        return (f'<figure><a class="slot" href="{esc(img.name)}" target="_blank" rel="noopener" style="--r:{ratio}">'
                f'<img src="{esc(img.name)}" alt="{esc(b["alt"])}" width="{w}" height="{h}" {load} decoding="async">'
                f'<span class="sr"> (opens full size in a new tab)</span></a>{cap}</figure>')

    count = words(page["headline"], page["summary"], page["outcome"], page["hero"].get("caption", ""))

    facts = page["facts"]
    assert len(facts) == 3 and all(len(f) == 2 for f in facts), f"{slug}: facts needs three [label, value] pairs"
    count += words(*[x for f in facts for x in f])
    facts_html = '<dl class="facts">' + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in facts) + "</dl>"
    outcome_html = f'<p class="out"><b>Outcome</b>{esc(page["outcome"])}</p>'

    count += words(*page["story"])
    story_html = "\n".join(f"<p>{esc(p)}</p>" for p in page["story"])

    for c in page["calls"]:
        assert c.get("call") and c.get("why"), f"{slug}: each call needs call and why"
        count += words(c["call"], c["why"])
    calls_html = ('<h2>The calls</h2><dl class="calls">'
                  + "".join(f"<div><dt>{esc(c['call'])}</dt><dd>{esc(c['why'])}</dd></div>" for c in page["calls"]) + "</dl>")

    gallery_html = ""
    if page.get("gallery"):
        g = page["gallery"]
        assert g.get("layout") in ("pair", "rail"), f"{slug}: gallery layout must be pair or rail"
        imgs = g.get("images", [])
        assert imgs and (g["layout"] != "pair" or len(imgs) == 2), f"{slug}: a pair takes exactly two images"
        count += words(*[i.get("caption", "") for i in imgs])
        gallery_html = f'<div class="gallery {g["layout"]}">' + "".join(image(i) for i in imgs) + "</div>"

    links_html = ""
    if page.get("links"):
        items = []
        for link in page["links"]:
            text, url = link.get("text", "").strip(), link.get("href", "").strip()
            assert text, f"{slug}: a link needs text"
            assert url.startswith("https://"), f"{slug}: link {text!r} must be https"
            count += words(text)
            items.append(f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(text)}&nbsp;<span class="ar" aria-hidden="true">↗</span></a>')
        links_html = f'<p class="links">{"".join(items)}</p>'

    assert count <= MAX_WORDS, f"{slug}: {count} words, the cap is {MAX_WORDS}"

    meta = "".join(f"<span>{esc(str(x))}</span>" for x in ("Built at work" if page.get("at_work") else page.get("label"), page["year"]) if x)
    if page.get("at_work"):
        meta += '<span><a href="/resume/">Resume&nbsp;<span class="ar" aria-hidden="true">→</span></a></span>'

    fill = {
        "SLUG": esc(slug), "TITLE": esc(page["title"]), "DESCRIPTION": esc(page["description"]), "META": meta,
        "HEADLINE": esc(page["headline"]), "SUMMARY": esc(page["summary"]), "FACTS": facts_html,
        "OUTCOME": outcome_html, "HERO": image(page["hero"], eager=True), "STORY": story_html,
        "CALLS": calls_html, "GALLERY": gallery_html, "LINKS": links_html,
    }
    out = template
    for k, v in fill.items():
        out = out.replace("{{" + k + "}}", v)
    assert "{{" not in out, f"{slug}: unfilled placeholder"
    (out_dir / "index.html").write_text(out)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(page["updated"])), f"{slug}: updated must be YYYY-MM-DD"
    lastmods[slug] = page["updated"]
    built += 1
    print(f"Wrote public/projects/{slug}/index.html ({count} words)")

# One sitemap entry per case study, right after /projects/; every other entry is left alone.
sitemap = ROOT / "public" / "sitemap.xml"
text = sitemap.read_text()
text = re.sub(r"\n  <url>\n    <loc>https://siddharthshah\.me/projects/[^/<]+/</loc>\n    <lastmod>[^<]*</lastmod>\n  </url>", "", text)
entries = "".join(f"\n  <url>\n    <loc>https://siddharthshah.me/projects/{s}/</loc>\n    <lastmod>{d}</lastmod>\n  </url>"
                  for s, d in sorted(lastmods.items()))
anchor = re.search(r"\n  <url>\n    <loc>https://siddharthshah\.me/projects/</loc>\n    <lastmod>[^<]*</lastmod>\n  </url>", text)
assert anchor, "sitemap.xml needs a /projects/ entry"
text = text[:anchor.end()] + entries + text[anchor.end():]
sitemap.write_text(text)
print(f"{built} case stud{'y' if built == 1 else 'ies'}; sitemap has {len(lastmods)} case-study entr{'y' if len(lastmods) == 1 else 'ies'}")
