#!/usr/bin/env python3
"""Hourly profile update, run by the systemd user timer in systemd/.

- status: Claude Code output tokens for the current week, expires in 7 days
  so it disappears on its own if this machine stays off;
- card: the list of public repos, committed as an address that isn't linked
  to the account, so the updates don't show up on the contribution graph.

--dry-run prints the status and renders the card into a temp dir instead.
"""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import render

ROOT = Path(__file__).resolve().parent.parent
USER = 'qokori'
MAX_REPOS = 6
HIDDEN = {USER, 'mvp-max', 'task-tracker-ws', 'cryptobrains'}  # never on the card
USAGE_HELPER = (Path.home() / '.local/share/gnome-shell/extensions/'
                'claude-usage@neorcage/usage_helper.py')
STATUS_TTL = timedelta(days=7)
BOT = ['-c', 'user.name=qokori-bot', '-c', 'user.email=bot@qokori.invalid']
SET_STATUS = '''mutation($message: String!, $expires: DateTime!) {
  changeUserStatus(input: {emoji: ":robot:", message: $message, expiresAt: $expires}) {
    status { message }
  }
}'''


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def git(*args):
    return run('git', '-C', str(ROOT), *args)


def human(n):
    for unit, size in (('B', 1e9), ('M', 1e6), ('k', 1e3)):
        if n >= size:
            return f'{n / size:.1f}'.rstrip('0').rstrip('.') + unit
    return str(n)


def update_status(dry_run):
    usage = json.loads(run(sys.executable, str(USAGE_HELPER)))
    week = next(p for p in usage['tokens']['periods'] if p['key'] == 'week')
    if not week['output']:
        print('status: no tokens this week, left as is')
        return
    message = f'claude wrote {human(week["output"])} tokens for me this week'
    if dry_run:
        print(f'status: {message}')
        return
    expires = (datetime.now(timezone.utc) + STATUS_TTL).strftime('%Y-%m-%dT%H:%M:%SZ')
    run('gh', 'api', 'graphql', '-f', f'query={SET_STATUS}',
        '-f', f'message={message}', '-f', f'expires={expires}')
    print(f'status: {message}')


def public_repos():
    repos = json.loads(run('gh', 'api', f'users/{USER}/repos?sort=pushed&per_page=100'))
    return [(r['name'], r['description'] or '') for r in repos
            if not r['fork'] and r['name'] not in HIDDEN][:MAX_REPOS]


def update_card(dry_run):
    if dry_run:
        out = Path(tempfile.mkdtemp(prefix='qokori-card-'))
        repos = public_repos()
        render.write_cards(repos, out)
        print(f'card: {", ".join(name for name, _ in repos)} -> {out}')
        return
    if (git('status', '--porcelain', '--untracked-files=no')
            or git('branch', '--show-current').strip() != 'main'):
        print('card: skipped, the checkout is dirty or not on main')
        return
    git('pull', '--ff-only', '-q')
    repos = public_repos()
    render.write_cards(repos)
    if not git('status', '--porcelain', 'assets'):
        print('card: up to date')
        return
    git(*BOT, 'commit', '-qm', 'update repo list', 'assets')
    git('push', '-q')
    print(f'card: pushed {", ".join(name for name, _ in repos)}')


def main():
    dry_run = '--dry-run' in sys.argv[1:]
    failed = False
    for step in (update_status, update_card):
        try:
            step(dry_run)
        except Exception as e:
            print(f'{step.__name__}: {getattr(e, "stderr", None) or e}', file=sys.stderr)
            failed = True
    sys.exit(failed)


if __name__ == '__main__':
    main()
