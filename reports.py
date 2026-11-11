"""Explicit, read-only mounts for HTML reports stored outside this repository."""
import json
from pathlib import Path
import re

REPORT_EXTENSIONS = {'.html','.htm','.js','.css','.json','.svg','.gif','.ico',
    '.woff','.woff2','.ttf','.eot','.otf','.txt','.zip','.pdf','.png','.jpg',
    '.jpeg','.webp','.csv','.tsv','.xls','.xlsx'}


def safe_root(root):
    root = Path(root).absolute()
    current = Path(root.anchor)
    for part in root.parts[1:]:
        if part == '..':
            raise ValueError('Parent traversal is not allowed in report roots')
        current = current/part
        if current.is_symlink():
            raise ValueError('Report roots must not contain symlinks')
    if not root.is_dir():
        raise ValueError('Configured report directory does not exist')
    return root


def safe_file(base, relative):
    parts = relative.split('/')
    if not parts or any(not p or p.startswith('.') or '\\' in p for p in parts):
        raise FileNotFoundError(relative)
    target = base
    for part in parts:
        target = target/part
        if target.is_symlink():
            raise FileNotFoundError(relative)
    if not target.resolve().is_relative_to(base.resolve()) or not target.is_file():
        raise FileNotFoundError(relative)
    return target


def load_config(config):
    if config is None:
        return [], [], {}
    config = Path(config).absolute()
    data = json.loads(config.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('reports'), list):
        raise ValueError('Config must contain a reports array')
    studies, reports, registry = [], [], {}
    for item in data['reports']:
        if not isinstance(item, dict):
            raise ValueError('Each report must be an object')
        key = item.get('id', '')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key) or key in registry:
            raise ValueError('Each report needs a unique alphanumeric id (dash/underscore allowed)')
        name, kind, location = item.get('name',key), item.get('kind','other'), item.get('path')
        if not all(isinstance(v,str) and v for v in (name,kind,location)):
            raise ValueError('Report name, kind and path must be non-empty strings')
        root = safe_root(config.parent/location)
        entry = item.get('entry')
        if entry is None:
            for candidate in ('index.html','home/index.html'):
                try:
                    safe_file(root,candidate)
                    entry = candidate
                    break
                except FileNotFoundError:
                    pass
        if not isinstance(entry,str) or Path(entry).suffix.lower() not in ('.html','.htm'):
            raise ValueError('Report entry must name an existing HTML file')
        safe_file(root,entry)
        registry[key] = str(root)
        studies.append(dict(id=key,name=name,kind=kind))
        # Never expose the private absolute mount path in the client catalog.
        reports.append(dict(study=key,name=name,kind=kind,path=entry,entry=entry,url=f'reports/{key}/{entry}'))
    return studies,reports,registry


def resolve(base, registry, route):
    key, separator, relative = route.partition('/')
    if not separator or key not in registry or Path(relative).suffix.lower() not in REPORT_EXTENSIONS:
        raise FileNotFoundError(route)
    parts = relative.split('/')
    if any(not p or p.startswith('.') or '\\' in p for p in parts):
        raise FileNotFoundError(route)
    try:
        root = safe_root(base/registry[key])
    except ValueError as error:
        raise FileNotFoundError(route) from error
    target = root
    for part in parts:
        exact = target/part
        if exact.is_symlink():
            raise FileNotFoundError(route)
        if exact.exists():
            target = exact
        else:
            if not target.is_dir():
                raise FileNotFoundError(route)
            matches = [p for p in target.iterdir() if p.name.casefold()==part.casefold()]
            if len(matches)!=1 or matches[0].is_symlink():
                raise FileNotFoundError(route)
            target = matches[0]
    return safe_file(root,target.relative_to(root).as_posix())
