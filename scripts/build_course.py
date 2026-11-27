"""Build the course page pieces from the files in course/, quizzes/ and slides/.

Quarto runs this before every render (see pre-render in _quarto.yml), so the
schedule, tutorial index, readings list, labs list, case study dates and the
data behind "This week" are always rebuilt from the CSV files. Nothing here
needs to be edited by hand.

Outputs (all git-ignored):
  _generated/*.md    raw HTML blocks included by index.qmd and case_studies.qmd
  assets/course.js   window.COURSE, read by assets/site.js in the browser
"""

import csv
import datetime as dt
import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSE = ROOT / "course"
GEN = ROOT / "_generated"

SYM = {"concept": "■", "workshop": "▲", "new": "●", "prep": "○",
       "case": "★", "off": "—", "final": "◆"}


def read_csv(name):
    with open(COURSE / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(s):
    return html.escape(s or "", quote=True)


def day_label(iso, end=None):
    if not iso:
        return "Exam slot"
    d = dt.date.fromisoformat(iso)
    if end:
        e = dt.date.fromisoformat(end)
        return f"{d:%b} {d.day}–{e.day}" if d.month == e.month else f"{d:%b} {d.day}–{e:%b} {e.day}"
    return f"{d:%a %b} {d.day}"


def raw(html_text):
    return "```{=html}\n" + html_text + "\n```\n"


def main():
    GEN.mkdir(exist_ok=True)
    schedule = read_csv("schedule.csv")
    readings = {r["slug"]: r for r in read_csv("readings.csv")}
    tutorials = read_csv("tutorials.csv")
    tut_by_file = {t["file"]: t for t in tutorials}
    units = {u["unit_no"]: u for u in read_csv("units.csv")}
    lab_titles = {l["n"]: l["title"] for l in read_csv("labs.csv")}

    # A tutorial counts as ready only once its .qmd exists.
    for t in tutorials:
        t["ready"] = (ROOT / f"{t['file']}.qmd").exists() and t["status"] == "ready"
    for r in readings.values():
        r["ready"] = (ROOT / f"reading-{r['slug']}.qmd").exists() and r["status"] == "ready"

    # Slides: slides/2027-02-12.pdf (or .pptx if CI has not converted it).
    slides = {}
    for p in sorted((ROOT / "slides").glob("*")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m and p.suffix.lower() in (".pdf", ".pptx"):
            if m.group(1) not in slides or p.suffix.lower() == ".pdf":
                slides[m.group(1)] = f"slides/{p.name}"

    def reading_items(field):
        out = []
        for item in filter(None, (field or "").split(";")):
            item = item.strip()
            if item.startswith("text:"):
                out.append({"title": item[5:], "href": ""})
            elif item.startswith("link:"):
                title, _, url = item[5:].partition("|")
                out.append({"title": title, "href": url, "external": True})
            else:
                slug, _, section = item.partition("#")
                r = readings.get(slug)
                if not r:
                    continue
                out.append({"title": r["title"], "slug": slug, "section": section,
                            "href": f"reading-{slug}.html" if r["ready"] else "",
                            "soon": not r["ready"]})
        return out

    rows = []
    for s in schedule:
        t = tut_by_file.get(s["tutorial"])
        rows.append({
            "n": s["n"], "date": s["date"], "end": s["end_date"], "week": s["week"],
            "unit": s["unit_no"], "concept": s["concept"], "kind": s["kind"],
            "topic": s["topic"], "in_class": s["in_class"], "lab": s["lab"],
            "due": s["due"], "note": s["note"],
            "label": day_label(s["date"], s["end_date"]),
            "readings": reading_items(s["readings"]),
            "tutorial": ({"file": t["file"], "title": t["title"],
                          "href": f"{t['file']}.html" if t["ready"] else ""} if t else None),
            "slides": slides.get(s["date"], ""),
        })

    # Case studies are numbered in schedule order; their prep day is the "prep" row before.
    cases, prep = [], None
    for r in rows:
        if r["kind"] == "prep":
            prep = r
        elif r["kind"] == "case":
            cases.append({"n": len(cases) + 1, "date": r["date"], "label": r["label"],
                          "prep": prep["label"] if prep else "", "unit": r["unit"],
                          "unit_name": units[r["unit"]]["name"],
                          "covers": units[r["unit"]]["concepts"], "note": r["note"]})
            prep = None
    case_of_date = {c["date"]: c["n"] for c in cases}

    # Labs: workshop from the lab column, due date from the due column.
    labs = {n: {"n": n, "title": lab_titles.get(n, f"Lab {n}"), "workshop": "", "due": ""}
            for n in lab_titles}
    for r in rows:
        if r["lab"] in labs:
            labs[r["lab"]]["workshop"] = r["label"]
        m = re.match(r"Lab (\d+)", r["due"] or "")
        if m and m.group(1) in labs:
            labs[m.group(1)]["due"] = r["label"]

    def due_html(due):
        m = re.match(r"Lab (\d+)", due or "")
        if m:
            return f'<a href="labs.html#lab-{m.group(1)}">Lab {m.group(1)}</a>'
        return esc(due)

    def readings_html(items):
        parts = []
        for it in items:
            if it["href"]:
                star = "" if it.get("external") else "★ "
                parts.append(f'<a href="{esc(it["href"])}">{star}{esc(it["title"])}</a>')
            elif it.get("soon"):
                parts.append(f'★ {esc(it["title"])} <span class="muted">(coming soon)</span>')
            else:
                parts.append(esc(it["title"]))
        return "<br>".join(parts)

    # ---- Schedule table -------------------------------------------------
    out = ['<div class="schedule-scroll"><table class="schedule">',
           '<thead><tr><th></th><th>Date</th><th></th><th>Topic</th><th>In class</th>'
           '<th>Read and quiz</th><th>Due</th></tr></thead><tbody>']
    cur_unit = None
    for r in rows:
        if r["unit"] and r["unit"] != cur_unit and r["kind"] != "final":
            cur_unit = r["unit"]
            out.append(f'<tr class="unit"><td colspan="7"><span class="unit-no">Unit {esc(cur_unit)}</span> '
                       f'{esc(units[cur_unit]["name"])}</td></tr>')
        k = r["kind"]
        cls = f"k-{k}"
        if k == "off":
            out.append(f'<tr class="{cls}"><td class="sym">—</td><td>{esc(r["label"])}</td><td></td>'
                       f'<td colspan="3"><em>{esc(r["topic"])}</em></td><td>{due_html(r["due"])}</td></tr>')
            continue
        topic = f'<b>{esc(r["topic"])}</b>'
        if r["slides"]:
            topic += f' · <a class="slides-link" data-date="{r["date"]}" href="{esc(r["slides"])}">slides</a>'
        if k == "case":
            topic += f' · <a href="case_studies.html#case-study-{case_of_date[r["date"]]}">study guide</a>'
        inclass = esc(r["in_class"])
        if r["tutorial"] and r["tutorial"]["href"]:
            inclass += f' · <a href="{r["tutorial"]["href"]}">tutorial</a>'
        if r["note"]:
            inclass += f' <span class="muted">({esc(r["note"])})</span>'
        concept = esc(r["concept"]) if k != "final" else "Final"
        out.append(f'<tr class="{cls}" data-date="{r["date"]}"><td class="sym">{SYM[k]}</td>'
                   f'<td>{esc(r["label"])}</td><td class="concept">{concept}</td><td>{topic}</td>'
                   f'<td>{inclass}</td><td>{readings_html(r["readings"])}</td>'
                   f'<td>{due_html(r["due"])}</td></tr>')
    out.append("</tbody></table></div>")
    meetings = sum(1 for r in rows if r["n"])
    (GEN / "schedule.md").write_text(raw("\n".join(out)), encoding="utf-8")

    # ---- Tutorials index --------------------------------------------------
    out = ['<div class="sheet-index">']
    for t in tutorials:
        code = re.sub(r"Concept (\d+)", lambda m: m.group(1).zfill(2), t["concept"])
        code = {"R toolkit": "R", "New": "New"}.get(code, code)
        body = (f'<span class="sheet-code">{esc(code)}</span>'
                f'<span class="sheet-title">{esc(t["title"])}</span>')
        if t["ready"]:
            out.append(f'<a class="sheet" href="{t["file"]}.html">{body}</a>')
        else:
            out.append(f'<div class="sheet soon">{body}<span class="muted">Coming soon</span></div>')
    out.append("</div>")
    (GEN / "tutorials.md").write_text(raw("\n".join(out)), encoding="utf-8")

    # ---- Readings list ----------------------------------------------------
    used = {}
    for r in rows:
        for it in r["readings"]:
            if it.get("slug"):
                used.setdefault(it["slug"], []).append(r["label"])
    out = ['<table class="plain-list"><tbody>']
    for i, r in enumerate(readings.values(), 1):
        title = (f'<a href="reading-{r["slug"]}.html">{esc(r["title"])}</a>' if r["ready"]
                 else f'{esc(r["title"])} <span class="muted">(coming soon)</span>')
        when = ", ".join(used.get(r["slug"], []))
        out.append(f'<tr><td class="num">{i}</td><td>{title}</td><td class="muted">{esc(when)}</td></tr>')
    out.append("</tbody></table>")
    (GEN / "readings.md").write_text(raw("\n".join(out)), encoding="utf-8")

    # ---- Labs list --------------------------------------------------------
    out = ['<table class="plain-list"><tbody>']
    for l in labs.values():
        ws = f'workshop {l["workshop"]}' if l["workshop"] else ""
        out.append(f'<tr><td class="num">{l["n"]}</td><td><a href="labs.html#lab-{l["n"]}">'
                   f'{esc(l["title"])}</a></td><td class="muted">{esc(ws)}</td>'
                   f'<td>{"due " + esc(l["due"]) if l["due"] else ""}</td></tr>')
    out.append("</tbody></table>")
    (GEN / "labs.md").write_text(raw("\n".join(out)), encoding="utf-8")

    # ---- Case study legend boxes -----------------------------------------
    for c in cases:
        ta = " Run by the TA." if "TA" in (c["note"] or "") else ""
        box = (f'<div class="legend-box"><div class="legend-title">Case Study {c["n"]}</div>'
               f'<span class="sym prep">○</span><span>Prep day, {esc(c["prep"])}</span>'
               f'<span class="sym case">★</span><span>Case study, {esc(c["label"])}</span>'
               f'<span class="sym muted">—</span><span class="muted">In class, closed book.{ta}</span></div>'
               f'<p>Covers {esc(c["covers"])}.</p>')
        (GEN / f"case_{c['n']}.md").write_text(raw(box), encoding="utf-8")

    # ---- This week section shell (filled in by site.js) -------------------
    svg = (ROOT / "assets" / "contours.svg").read_text(encoding="utf-8")
    week = (f'<section id="this-week" class="this-week">{svg}'
            '<div class="week-head"><h2>This week</h2><span class="week-label"></span>'
            '<p class="week-unit muted"></p></div><div class="week-days">'
            '</div></section>')
    (GEN / "week.md").write_text(raw(week), encoding="utf-8")

    # ---- Data for the browser ---------------------------------------------
    quizzes = {}
    for p in sorted((ROOT / "quizzes").glob("*.json")):
        quizzes[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    data = {"rows": rows, "units": units, "cases": cases,
            "readings": list(readings.values()),
            "tutorials": tutorials, "quizzes": quizzes}
    (ROOT / "assets" / "course.js").write_text(
        "window.COURSE = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"build_course: {meetings} meetings, {len(cases)} case studies, "
          f"{len(slides)} slide decks, {len(quizzes)} quizzes")


if __name__ == "__main__":
    main()
