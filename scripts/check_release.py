#!/usr/bin/env python3
"""Validate tracked source and optionally ZIP only the explicitly allowed files."""
import argparse
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'.gitignore','README.md','AGENTS.md','config.example.json','server.py','reports.py','presentation.py',
    'static/index.html','static/style.css','static/theme.css','static/nav.css','static/app.js','static/nav.js','static/favicon.svg',
    'tests/test_reports.py','tests/test_presentation.py','tests/test_server.py','tests/nav.test.cjs','tests/browser.spec.cjs',
    'scripts/check_release.py'}


def check():
    tracked = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    tracked = [p for p in tracked if p]
    if not tracked:
        raise SystemExit('No tracked files. Stage the source before checking.')
    if set(tracked) != ALLOWED:
        raise SystemExit(f'Unexpected tracked paths: {sorted(set(tracked)-ALLOWED)}; missing: {sorted(ALLOWED-set(tracked))}')
    for name in tracked:
        path = ROOT/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 200_000:
            raise SystemExit(f'Unexpected source file or size: {name}')
        content = path.read_bytes()
        staged = subprocess.check_output(['git','show',f':{name}'],cwd=ROOT)
        if content != staged:
            raise SystemExit(f'Working file differs from staged content; review and stage again: {name}')
        # Split patterns here so the validator itself does not match its checks.
        forbidden = [b'-----BEGIN '+b'PRIVATE KEY', b'-----BEGIN '+b'OPENSSH PRIVATE KEY',
                     b'ghp'+b'_', b'github'+b'_pat_', b'/data/'+b'horse/']
        private_home = re.search(rb"(?:^|[\s\"'=])/(?:home|Users)/[^/\s]+/", content)
        if private_home or any(pattern in content for pattern in forbidden):
            raise SystemExit(f'Private credential/path marker found: {name}')
    return tracked


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path)
    args=parser.parse_args()
    names=check()
    if args.archive:
        archive=args.archive.absolute()
        if archive.exists():raise SystemExit('Archive exists; choose a new filename')
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as out:
            for name in names:out.write(ROOT/name,'omics_explorer/'+name)
    print(f'Validated {len(names)} staged source files; no unexpected paths or known credential/path markers.')
