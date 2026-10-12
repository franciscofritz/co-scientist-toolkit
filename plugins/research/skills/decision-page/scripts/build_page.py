#!/usr/bin/env python3
"""Fill the decision-page template with a page's data.

    python3 build_page.py page-data.json page.html

page-data.json holds {"title", "lede", "groups": [...]}, in the shape described in SKILL.md.
The script checks that shape, puts the data into the template's PAGE block, sets the <title>,
and writes page.html. It stops with a message, writing nothing, if the data is malformed.
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "decision-page.html")


def problems(d):
    out = []
    for k in ("title", "lede", "groups"):
        if k not in d:
            out.append(f"missing top-level key {k!r}")
    ids = set()
    for g in d.get("groups", []):
        for k in ("id", "title", "cards"):
            if k not in g:
                out.append(f"group {g.get('id', '?')}: missing {k!r}")
        for c in g.get("cards", []):
            cid = c.get("id", "?")
            if cid in ids:
                out.append(f"card id {cid!r} is used twice")
            ids.add(cid)
            for k in ("id", "title", "why"):
                if not c.get(k):
                    out.append(f"card {cid}: missing or empty {k!r}")
            if not c.get("detail"):
                out.append(f"card {cid}: 'detail' needs at least one paragraph")
            if "items" in c:
                if not c.get("itemVerb"):
                    out.append(f"card {cid}: a card of items needs 'itemVerb'")
                if not c["items"]:
                    out.append(f"card {cid}: 'items' is empty")
                item_ids = [it.get("id") for it in c["items"]]
                if len(set(item_ids)) != len(item_ids) or None in item_ids:
                    out.append(f"card {cid}: item ids must be present and distinct")
            elif "options" in c:
                opt_ids = [o.get("id") for o in c["options"]]
                if len(c["options"]) < 2:
                    out.append(f"card {cid}: a choice needs at least two options")
                if c.get("rec") not in opt_ids:
                    out.append(f"card {cid}: 'rec' must be one of the option ids {opt_ids}")
            else:
                out.append(f"card {cid}: needs either 'options' or 'items'")
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: build_page.py page-data.json page.html")
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    bad = problems(data)
    if bad:
        sys.exit("page data not built:\n  " + "\n  ".join(bad))
    page = open(TEMPLATE, encoding="utf-8").read()
    start = page.index("const PAGE = {")
    end = page.index("\n};", start) + 3
    block = "const PAGE = " + json.dumps(data, indent=1, ensure_ascii=False).replace("</", "<\\/") + ";"
    page = page[:start] + block + page[end:]
    page = page.replace("<title>__TITLE__</title>", f"<title>{html.escape(data['title'])}</title>", 1)
    open(sys.argv[2], "w", encoding="utf-8").write(page)
    n = sum(len(g["cards"]) for g in data["groups"])
    print(f"wrote {sys.argv[2]}: {n} cards in {len(data['groups'])} groups")


if __name__ == "__main__":
    main()
