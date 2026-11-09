#!/usr/bin/env python3
"""Regenerate card.svg from live GitHub stats. Needs GH_TOKEN."""
import json
import os
import urllib.request
from collections import Counter
from datetime import date
from html import escape
from xml.dom.minidom import parseString

LOGIN = "marctaylor700"
WIDTH = 60  # characters in the info column
CHAR_W, LINE_H = 8.1, 18  # px per character at font-size 13 (SF Mono is ~8.03); nudge if rows clip


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


# ponytail: first 100 repos only (owned, org and collaborator), paginate if you ever pass that
u = gql(
    "createdAt followers{totalCount}"
    " repositories(ownerAffiliations:[OWNER,ORGANIZATION_MEMBER,COLLABORATOR],isFork:false,first:100,"
    "orderBy:{field:CREATED_AT,direction:ASC})"
    "{totalCount nodes{owner{login} stargazerCount"
    " languages(first:20,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}"
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
# Rank languages by bytes of code across every repo, keeping those above 1% of the total.
size = Counter()
for n in repos["nodes"]:
    for e in n["languages"]["edges"]:
        size[e["node"]["name"]] += e["size"]
langs = [name for name, s in size.most_common() if s * 100 >= sum(size.values())]


def take(key, names):
    """Build a row from as many leading names as fit on one line, removing them from names."""
    picked = []
    while names and len(key) + len(", ".join(picked + names[:1])) + 4 <= WIDTH:
        picked.append(names.pop(0))
    return key, ", ".join(picked)


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
    take("Languages.Top", langs),
    take("Languages.More", langs),
    ("Bio", "green was for the money and gold was for the honey"),
    None,
    "Contact",
    ("GitHub", f"github.com/{LOGIN}"),
    None,
    "GitHub Stats",
    ("Repos", f"{repos['totalCount']} (Contributed: {u['repositoriesContributedTo']['totalCount']})"),
    ("Stars", sum(n["stargazerCount"] for n in repos["nodes"] if n["owner"]["login"] == LOGIN)),
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


# The classic "crab" invader, in two frames so its legs wiggle.
INVADER = ("""
..#.....#..
...#...#...
..#######..
.##.###.##.
###########
#.#######.#
#.#.....#.#
...##.##...
""", """
..#.....#..
#..#...#..#
#.#######.#
###.###.###
###########
.#########.
..#.....#..
.#.......#.
""")
PX, SHOT_S, INFO_X, TOP = 3, 0.8, 130, 36  # sprite pixel size, seconds per shot, text column x, first baseline y


def sprite(art):
    """One SVG path with a PX-sized square for every # in the pixel art."""
    return "".join(f"M{x * PX} {y * PX}h{PX}v{PX}h-{PX}z"
                   for y, row in enumerate(art.split()) for x, c in enumerate(row) if c == "#")


# The invader visits every non-blank row in turn, one shot each, then loops back to the top.
targets = [i for i, row in enumerate(ROWS) if row is not None]
cycle = len(targets) * SHOT_S
nose, mid = len(INVADER[0].split()[0]) * PX, len(INVADER[0].split()) * PX / 2
reach = INFO_X - 20 - nose - 24  # how far a shot flies before it meets the text
# A shot lands 70% of the way through its slot, so row k starts its recoil at (k + 0.7) shots in.
texts = "\n".join(
    f'<text x="{INFO_X}" y="{TOP + i * LINE_H}" style="animation-delay:{(k + 0.7) * SHOT_S:g}s">{line(ROWS[i])}</text>'
    for k, i in enumerate(targets))
patrol = "".join(f"{100 * k / len(targets):g}%{{transform:translateY({i * LINE_H}px)}}" for k, i in enumerate(targets))
# The shot and spark sit inside the invader's group, so they fire along whichever row it is on.
css = f"""text{{white-space:pre;animation:recoil {cycle:g}s ease-out infinite}}
.h{{fill:#f0f6fc;font-weight:bold}}.k{{fill:#ffa657}}.d{{fill:#484f58}}.v{{fill:#a5d6ff}}
.ship{{animation:patrol {cycle:g}s step-end infinite}}
.f1,.f2{{animation:legs {SHOT_S}s step-end infinite}}.f2{{opacity:0;animation-delay:-{SHOT_S / 2}s}}
.shot{{animation:shot {SHOT_S}s linear infinite}}.spark{{opacity:0;animation:spark {SHOT_S}s linear infinite}}
@keyframes patrol{{{patrol}}}
@keyframes legs{{0%{{opacity:1}}50%{{opacity:0}}}}
@keyframes shot{{70%{{transform:translateX({reach}px);opacity:1}}71%,100%{{transform:translateX({reach}px);opacity:0}}}}
@keyframes spark{{0%,69%{{opacity:0}}72%{{opacity:1}}100%{{opacity:0}}}}
@keyframes recoil{{0%{{transform:translateX(7px);opacity:.35}}{100 * 0.4 / cycle:.3g}%,100%{{transform:none;opacity:1}}}}
@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{INFO_X + WIDTH * CHAR_W + 20:.0f}" height="{TOP + (len(ROWS) - 1) * LINE_H + 22}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace" font-size="13" fill="#8b949e">
<style>{css}</style>
<rect width="100%" height="100%" rx="10" fill="#161b22"/>
<g transform="translate(20 {TOP - 4 - mid:g})"><g class="ship" fill="#3fb950" shape-rendering="crispEdges">
<path class="f1" d="{sprite(INVADER[0])}"/><path class="f2" d="{sprite(INVADER[1])}"/>
<rect class="shot" x="{nose + 4}" y="{mid - 1.5:g}" width="8" height="3" fill="#f0f6fc"/>
<rect class="spark" x="{nose + reach + 14}" y="{mid - 5.5:g}" width="3" height="11" fill="#ffa657"/>
</g></g>
{texts}
</svg>
"""
parseString(svg)  # refuse to write a card that isn't well-formed XML
with open("card.svg", "w") as f:
    f.write(svg)
