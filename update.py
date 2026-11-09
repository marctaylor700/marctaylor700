#!/usr/bin/env python3
"""Regenerate card.svg from ascii.txt plus live GitHub stats. Needs GH_TOKEN."""
import json
import os
import urllib.request
from collections import Counter
from datetime import date
from html import escape
from xml.dom.minidom import parseString

LOGIN = "marctaylor700"
WIDTH = 60  # characters in the info column
CHAR_W, LINE_H = 8.1, 18  # px per character at font-size 13 (SF Mono is ~8.03); nudge if columns collide


def gql(fields):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": '{user(login:"%s"){%s}}' % (LOGIN, fields)}).encode(),
        headers={"Authorization": "bearer " + os.environ["GH_TOKEN"]},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if body.get("errors"):
        raise SystemExit(body["errors"])
    return body["data"]["user"]


# ponytail: first 100 owned repos only, paginate if you ever own more
u = gql(
    "createdAt followers{totalCount}"
    " repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:CREATED_AT,direction:ASC})"
    "{totalCount nodes{stargazerCount primaryLanguage{name}}}"
    " repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount}"
    " contributionsCollection{contributionYears}"
)
# The API only returns one year of contributions per call, so ask for every year at once via aliases.
per_year = gql(" ".join(
    f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z")'
    "{contributionCalendar{totalContributions}}"
    for y in u["contributionsCollection"]["contributionYears"]
))
contributions = sum(y["contributionCalendar"]["totalContributions"] for y in per_year.values())

repos = u["repositories"]
langs = Counter(n["primaryLanguage"]["name"] for n in repos["nodes"] if n["primaryLanguage"])
y0, m0, d0 = map(int, u["createdAt"][:10].split("-"))
today = date.today()
months = (today.year - y0) * 12 + today.month - m0 - (today.day < d0)

# Edit freely. ("Key", "value") is a row, a bare string is a section header, None is a blank line.
ROWS = [
    f"{LOGIN}@github",
    ("OS", "macOS"),
    ("Shell", "zsh"),
    ("Uptime", f"{months // 12} years, {months % 12} months on GitHub"),
    ("Host", "eVisit"),
    ("Location", "Arizona"),
    ("Languages", ", ".join(name for name, _ in langs.most_common(5))),
    ("Bio", "green was for the money and gold was for the honey"),
    None,
    "Contact",
    ("GitHub", f"github.com/{LOGIN}"),
    None,
    "GitHub Stats",
    ("Repos", f"{repos['totalCount']} (Contributed: {u['repositoriesContributedTo']['totalCount']})"),
    ("Stars", sum(n["stargazerCount"] for n in repos["nodes"])),
    ("Followers", u["followers"]["totalCount"]),
    ("Contributions", f"{contributions:,}"),
]


def line(row):
    if row is None:
        return ""
    if isinstance(row, str):
        return f'<tspan class="h">{escape(row)}</tspan> ' + "─" * (WIDTH - len(row) - 1)
    key, value = row[0], str(row[1])
    dots = WIDTH - len(key) - len(value) - 3
    assert dots >= 1, f"row too long for WIDTH={WIDTH}: {key}"
    return (f'<tspan class="k">{escape(key)}</tspan>: <tspan class="d">{"." * dots}</tspan> '
            f'<tspan class="v">{escape(value)}</tspan>')


def column(x, lines, cls=""):
    return "\n".join(f'<text x="{x:.0f}" y="{32 + i * LINE_H}"{cls}>{l}</text>' for i, l in enumerate(lines))


with open("ascii.txt") as f:
    art = f.read().splitlines()
info_x = 20 + max(map(len, art)) * CHAR_W + 24
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{info_x + WIDTH * CHAR_W + 20:.0f}" height="{max(len(art), len(ROWS)) * LINE_H + 30}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace" font-size="13" fill="#8b949e">
<style>text{{white-space:pre}}.a{{fill:#c9d1d9}}.h{{fill:#f0f6fc;font-weight:bold}}.k{{fill:#ffa657}}.d{{fill:#484f58}}.v{{fill:#a5d6ff}}</style>
<rect width="100%" height="100%" rx="10" fill="#161b22"/>
{column(20, map(escape, art), ' class="a"')}
{column(info_x, map(line, ROWS))}
</svg>
"""
parseString(svg)  # refuse to write a card that isn't well-formed XML
with open("card.svg", "w") as f:
    f.write(svg)
