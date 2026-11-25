#!/usr/bin/env python3
"""Write public/os/index.html from a checkout of the os rules repo.

    python3 scripts/build-os.py [path/to/os]

The os checkout comes from the argument, else $OS_REPO, else ../os next to this repo.
It reads rules/*.md (frontmatter plus the Why and Example paragraphs), tests/*.yaml and
tests/results.json, and fills scripts/os.template.html. Needs PyYAML.
"""
import html
import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OS_REPO", ROOT.parent / "os")).resolve()
GITHUB = "https://github.com/bigsidd/os"
DECISIONS = {"build", "refuse", "ask"}

# Short labels for the desk's stations; a rule without one uses its title.
SHORT = {
    "who-is-it-for": "Who is it for?",
    "what-are-they-really-after": "What are they after?",
    "does-it-beat-what-they-do-now": "Beats what they do now?",
    "know-who-youre-not-serving": "Who you're not serving",
    "most-ideas-dont-work": "Most ideas don't work",
    "cheapest-answer-first": "Cheapest answer first",
    "rough-not-hollow": "Rough, not hollow",
    "make-the-first-step-easy": "Easy first step",
    "say-what-should-change": "Say what should change",
    "only-ask-what-changes-the-decision": "Only ask what changes it",
    "code-before-a-model": "Code before a model",
    "show-where-it-breaks": "Show where it breaks",
    "play-it-forward": "Play it forward",
    "rank-what-matters": "Rank what matters",
}
WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()


def word(n):
    return WORDS[n] if n < len(WORDS) else str(n)


def e(s):
    return html.escape(s, quote=True)


def paragraph(body, label, slug):
    m = re.search(rf"^\*\*{label}\.\*\*\s*(.+?)(?:\n\s*\n|\Z)", body, re.S | re.M)
    assert m, f"{slug}: no **{label}.** paragraph"
    return " ".join(m.group(1).split())


# ---------- rules ----------
rules = []
for path in sorted((OS / "rules").glob("*.md")):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        continue  # README.md, retired.md
    _, front, body = text.split("---\n", 2)
    fm = yaml.safe_load(front)
    slug = fm["name"]
    assert slug == path.stem, f"{path.name}: name is {slug!r}"
    title = re.search(r"^# (.+)$", body, re.M)
    assert title, f"{slug}: no # title"
    decides = list(fm["decides"])
    weigh = decides == ["weigh"]
    assert weigh or set(decides) <= DECISIONS, f"{slug}: decides {decides}"
    rules.append({
        "slug": slug, "order": int(fm["order"]), "title": title.group(1).strip(), "rule": fm["rule"].strip(),
        "weigh": weigh, "fires": fm["fires_when"].strip(), "notw": fm["not_when"].strip(),
        "credit": (fm.get("credit") or "").strip(),
        "why": paragraph(body, "Why", slug), "ex": paragraph(body, "Example", slug),
    })
rules.sort(key=lambda r: r["order"])
assert [r["order"] for r in rules] == list(range(1, len(rules) + 1)), "rule order must run 1..n"
by_slug = {r["slug"]: r for r in rules}

# ---------- cases ----------
cases = []
for path in sorted((OS / "tests").glob("*.yaml")):
    slug = path.stem
    assert slug in by_slug, f"tests/{path.name} has no rule"
    for c in yaml.safe_load(path.read_text(encoding="utf-8")):
        x = c["expect"]
        kind = next(k for k in ("cites", "weighs", "not") if k in x)
        d = x["decision"]
        ds = d if isinstance(d, list) else [d]
        assert ds and set(ds) <= DECISIONS, f"{slug}/{c['title']}: decision {d!r}"
        assert x[kind] in by_slug, f"{slug}/{c['title']}: unknown rule {x[kind]!r}"
        assert (kind == "weighs") == by_slug[x[kind]]["weigh"] or kind == "not", f"{slug}/{c['title']}: {kind} on the wrong kind of rule"
        cases.append({"f": slug, "t": " ".join(c["title"].split()), "b": " ".join(c["body"].split()),
                      "d": ds if len(ds) > 1 else ds[0], "r": x[kind], "k": kind})
untested = sorted(set(by_slug) - {c["f"] for c in cases})
assert not untested, f"rules with no test cases: {untested}"

# ---------- results ----------
res = json.loads((OS / "tests" / "results.json").read_text(encoding="utf-8"))
ran = sorted(tuple(x) for x in res["cases_run"])
have = sorted((c["f"], c["t"]) for c in cases)
if ran != have:
    sys.exit(f"tests/results.json ran a different set of cases than tests/ holds ({len(ran)} vs {len(have)}); "
             "rerun the eval before publishing its numbers")
assert res["cases"] == len(cases) and res["calls"] == res["total"] == len(cases) * res["samples"], "results.json doesn't add up"
assert sum(v["passed"] for v in res["per_rule"].values()) == res["passed"], "per_rule doesn't sum to passed"
assert set(res["per_rule"]) == set(by_slug), "results.json covers different rules"
pct = round(100 * res["passed"] / res["total"])
per_bar = res["bar"]["per_rule"]
below = [s for s in sorted(by_slug, key=lambda s: by_slug[s]["order"])
         if res["per_rule"][s]["passed"] / res["per_rule"][s]["total"] < per_bar]
assert sorted(below) == sorted(res.get("below_bar_rules", below)), "below_bar_rules disagrees with per_rule"


def rule_link(slug):
    return f'<a href="#r-{slug}">{e(by_slug[slug]["title"])}</a>'


def join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


y, m, d = (int(p) for p in res["date"].split("-"))
date = f'{["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][m - 1]} {d}, {y}'
note = (f'Run against <a href="https://midwatch.siddharthshah.me/">Midwatch</a>&#x27;s planner on {date}, '
        f'{res["samples"]} samples per case. The bar is {round(100 * res["bar"]["overall"])}% '
        + ("and it&#x27;s met." if res["bar_met"] else "and it isn&#x27;t met yet."))
if below:
    pr = res["per_rule"]
    low = min(pr[s]["passed"] / pr[s]["total"] for s in below)
    weakest = [s for s in below if pr[s]["passed"] / pr[s]["total"] == low]
    counts = {(pr[s]["passed"], pr[s]["total"]) for s in weakest}
    at = (f'at {pr[weakest[0]]["passed"]} of {pr[weakest[0]]["total"]}, ' if len(counts) == 1
          else f'at {round(100 * low)}%, ')
    verb = "is" if len(weakest) == 1 else "are"
    note += (f' {word(len(below)).capitalize()} of the {word(len(rules))} rules are under the {round(100 * per_bar)}% per-rule bar; '
             f'the weakest, {at}{verb} {join([rule_link(s) for s in weakest])}.')
if res.get("regressions"):
    titles = [f"&quot;{e(x.split(': ', 1)[1])}&quot;" for x in res["regressions"]]
    n = len(titles)
    note += (f' {word(n).capitalize()} {"case" if n == 1 else "cases"} that passed every run last time '
             f'{"misses" if n == 1 else "miss"} at least once now: {join(titles)}.')


def miss_kind(reason):
    if reason.startswith("decided refuse,"):
        return "refused"
    if re.match(r"cited (?!nothing\b)[a-z-]+, expected", reason):
        return "neighbour"
    if reason.startswith("invalid plan:"):
        return "invalid"
    return None


# What the misses were, ordered by failed runs. Each failed run leaves one reason and the list is
# de-duplicated. A case's split is exact when its reasons share one kind (they cover every failed run)
# or there are as many reasons as failed runs; otherwise it is unknown, and no group is ranked.
misses, exact = {}, True
for f in res["failures"]:
    kinds = [miss_kind(r) for r in f["reasons"]]
    if len(set(kinds)) == 1:
        if kinds[0]:
            misses[kinds[0]] = misses.get(kinds[0], 0) + f["samples_failed"]
    elif len(kinds) == f["samples_failed"]:
        for k in kinds:
            if k:
                misses[k] = misses.get(k, 0) + 1
    else:
        exact = False
miss = {"refused": "the planner refusing where the case expected a build or a question",
        "neighbour": "citing a neighbouring rule instead of the one the case tests",
        "invalid": "a plan the checks reject as invalid"}
top = sorted(misses, key=lambda k: (-misses[k], list(miss).index(k)))[:2] if exact else []
if len(top) == 2:
    note += f" The biggest group of failed runs is {miss[top[0]]}; {miss[top[1]]} comes next."
elif top:
    note += f" The biggest group of failed runs is {miss[top[0]]}."
note += f' <a href="{GITHUB}/blob/main/tests/results.json">The full results</a>.'

# ---------- markup ----------
n_weigh = sum(r["weigh"] for r in rules)
stations = "\n".join(
    '<li' + (' class="w"' if r["weigh"] else '') + f'><button type="button" class="st{" weigh" if r["weigh"] else ""}" data-s="{r["slug"]}">'
    f'<span class="sn">{r["order"]:02d}</span><span class="sl">{e(SHORT.get(r["slug"], r["title"]))}</span></button></li>'
    for r in rules)
cards = "\n".join(
    f'<li class="card{" weigh" if r["weigh"] else ""}" id="r-{r["slug"]}" data-i="{i}">'
    f'<div class="front"><span class="cn">{r["order"]:02d}</span>'
    + ('<span class="tag">Weighs</span>' if r["weigh"] else '') +
    f'<h3 class="ct">{e(r["title"])}</h3><p class="cr">{e(r["rule"])}</p></div>'
    f'<div class="back"><p><b>Why.</b> {e(r["why"])}</p><p><b>Example.</b> {e(r["ex"])}</p>'
    f'<dl><dt>Fires when</dt><dd>{e(r["fires"])}</dd><dt>Not when</dt><dd>{e(r["notw"])}</dd>'
    f'{"<dt>From</dt><dd>" + e(r["credit"]) + "</dd>" if r["credit"] else ""}</dl></div></li>'
    for i, r in enumerate(rules))

first_i = next((i for i, c in enumerate(cases) if c["t"] == "Add a stats page"),
               next(i for i, c in enumerate(cases) if c["k"] == "cites"))
first = cases[first_i]
fds = first["d"] if isinstance(first["d"], list) else [first["d"]]
fr = by_slug[first["r"]]
end = "" if fr["title"][-1:] in "?!." else "."
how = {"cites": f'citing {rule_link(first["r"])}{end}', "weighs": f'weighing it with {rule_link(first["r"])}{end}',
       "not": f'and {rule_link(first["r"])} must stay quiet.'}[first["k"]]
first_cap = (f'From <a href="{GITHUB}/blob/main/tests/{first["f"]}.yaml">the test suite</a>: this request should get '
             + " or ".join(f"<b>{x}</b>" for x in fds) + f", {how}")
assert first["k"] != "not", "the opening case should be one where a rule fires"

data = json.dumps({
    "first": first_i,
    "cases": cases,
    "titles": {r["slug"]: r["title"] for r in rules},
    "rules": {r["slug"]: {"fires": r["fires"], "notw": r["notw"], **({"weigh": 1} if r["weigh"] else {})} for r in rules},
}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

fill = {
    "N_RULES": str(len(rules)), "N_WORD": word(len(rules)), "N_CAP": word(len(rules)).capitalize(),
    "N_CASES": str(len(cases)), "W_WORD": word(n_weigh),
    "BOARD_COLS": str((len(rules) + 1) // 2), "W_SPAN": str(6 // n_weigh if n_weigh and 6 % n_weigh == 0 else 2),
    "STATIONS": stations, "CARDS": cards, "DATA": data,
    "FIRST_T": e(first["t"]), "FIRST_B": e(first["b"]), "FIRST_R": e(fr["title"]),
    "FIRST_KIND": "Weighs" if first["k"] == "weighs" else "Cites",
    "FIRST_DCLASS": "either" if len(fds) > 1 else fds[0], "FIRST_DTEXT": " or ".join(x.upper() for x in fds),
    "FIRST_WHY": e(fr["fires"]), "FIRST_CAP": first_cap,
    "PASSED": str(res["passed"]), "TOTAL": str(res["total"]), "PCT": str(pct), "NOTE": note,
}
page = (ROOT / "scripts" / "os.template.html").read_text(encoding="utf-8")
page = re.sub(r"\{\{([A-Z_]+)\}\}", lambda mt: fill[mt.group(1)], page)
assert "{{" not in page
out = ROOT / "public" / "os" / "index.html"
out.write_text(page, encoding="utf-8")
print(f"Wrote {out.relative_to(ROOT)}: {len(rules)} rules, {len(cases)} cases, {res['passed']}/{res['total']} passed on {res['date']}")
