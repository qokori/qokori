#!/usr/bin/env python3
"""The heart-monitor line on the contribution graph.

The graph is a canvas of 7 rows (Sunday to Saturday) and one column per week.
PATTERN is a loop of columns laid out week by week from EPOCH, so the line
scrolls left by itself as the one-year window moves. Every lit day gets
COMMITS empty commits in the private canvas repo; nothing is ever removed,
and days missed while the laptop was off are filled in on the next run.

Usage: pulse.py preview FILE.svg   how the graph will look (dark theme)
"""
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = 'qokori/pulse'
CLONE = Path.home() / '.local/share/qokori/pulse'
AUTHOR = 'qokori <191158449+qokori@users.noreply.github.com>'
COMMITS = 20  # per lit day, above the real daily max, so the line gets the darkest shade
EPOCH = date(2024, 11, 10)  # a Sunday, week 0 of the loop; puts ЖИВ at the right edge at launch
WEEKS = 53  # columns on the graph


def glyph(*rows):
    return [{r for r, row in enumerate(rows) if row[c] == '#'} for c in range(len(rows[0]))]


FLAT, GAP = [{3}], [set()]
BEAT = [{2}, {3}, {4}, {1, 2, 3, 4}, {0}, {1, 2, 3, 4, 5}, {4}, {3}, {2}, {2}, {3}]  # P Q R S T
ZHE = glyph('#.#.#', '#.#.#', '.###.', '..#..', '.###.', '#.#.#', '#.#.#')
I = glyph('#...#', '#...#', '#..##', '#.#.#', '##..#', '#...#', '#...#')
VE = glyph('####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.')
PATTERN = (FLAT * 3 + BEAT + FLAT * 3 + BEAT + FLAT * 2
           + GAP + ZHE + GAP + I + GAP + VE + GAP)


def sunday(d):
    return d - timedelta(days=(d.weekday() + 1) % 7)


def lit(d):
    week = (sunday(d) - EPOCH).days // 7
    return (d.weekday() + 1) % 7 in PATTERN[week % len(PATTERN)]


def window(end):
    start = sunday(end) - timedelta(weeks=WEEKS - 1)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def today():
    return datetime.now(timezone.utc).date()


def git(*args, check=True, **kw):
    return subprocess.run(['git', '-C', str(CLONE), *args], check=check,
                          capture_output=True, text=True, **kw)


def missing(end):
    have = Counter(git('log', '--format=%ad', '--date=short', check=False).stdout.split())
    return {d: COMMITS - have[d.isoformat()] for d in window(end)
            if lit(d) and have[d.isoformat()] < COMMITS}


def write(todo):
    """Append the commits in date order with git fast-import, noon UTC each."""
    stream, parent = [], git('rev-parse', '-q', '--verify', 'refs/heads/main', check=False).returncode == 0
    for d, n in sorted(todo.items()):
        ts = int(datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc).timestamp())
        for _ in range(n):
            stream += ['commit refs/heads/main', f'author {AUTHOR} {ts} +0000',
                       f'committer {AUTHOR} {ts} +0000', 'data 5', 'pulse']
            if parent:
                stream.append('from refs/heads/main^0')
                parent = False
            stream.append('')
    git('fast-import', '--quiet', input='\n'.join(stream) + '\n')


def sync(dry_run=False):
    if not CLONE.exists():
        if dry_run:
            todo = {d: COMMITS for d in window(today()) if lit(d)}
            print(f'pulse: would clone {REPO} and add {sum(todo.values())} commits on {len(todo)} days')
            return
        CLONE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['gh', 'repo', 'clone', REPO, str(CLONE), '--', '-q'],
                       check=True, capture_output=True)
    todo = missing(today())
    total = sum(todo.values())
    if not todo:
        print('pulse: up to date')
    elif dry_run:
        print(f'pulse: would add {total} commits on {len(todo)} days')
    else:
        write(todo)
        git('push', '-q', 'origin', 'main')
        print(f'pulse: added {total} commits on {len(todo)} days')


def preview(path):
    """Lit days at the darkest shade, real days scaled against COMMITS, as GitHub will."""
    query = '{viewer{contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'
    weeks = json.loads(subprocess.run(['gh', 'api', 'graphql', '-f', f'query={query}'], check=True,
                                      capture_output=True, text=True).stdout)
    real = {day['date']: day['contributionCount'] for week in
            weeks['data']['viewer']['contributionsCollection']['contributionCalendar']['weeks']
            for day in week['contributionDays']}
    colors = ['#151b23', '#033a16', '#196c2e', '#2ea043', '#56d364']
    days = window(today())
    cell, gap = 10, 3
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WEEKS * (cell + gap) + 20}" '
           f'height="{7 * (cell + gap) + 20}"><rect width="100%" height="100%" fill="#0d1117"/>']
    for i, d in enumerate(days):
        count = real.get(d.isoformat(), 0)
        level = 4 if lit(d) else min(4, math.ceil(4 * count / COMMITS))
        x, y = 10 + (i // 7) * (cell + gap), 10 + (d.weekday() + 1) % 7 * (cell + gap)
        out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{colors[level]}"/>')
    Path(path).write_text('\n'.join(out) + '</svg>\n')


if __name__ == '__main__':
    if sys.argv[1:2] == ['preview']:
        preview(sys.argv[2])
    else:
        sys.exit(__doc__)
