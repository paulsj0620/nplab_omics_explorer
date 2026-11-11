#!/usr/bin/env python3
"""Read-only LAN result browser. Restricts peers to explicitly configured networks."""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
import logging
import mimetypes
from pathlib import Path
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
from reports import load_config, resolve
from presentation import report_script, report_html, report_css

class Catalog:
    def __init__(self, config=None):
        self.config = Path(config).absolute() if config else None
        self.base = self.config.parent if self.config else HERE
        self.snapshot = (b'', frozenset(), {})

    def refresh(self):
        studies, reports, registry = load_config(self.config)
        data = dict(reports=reports, mode='live', generated=datetime.now(timezone.utc).isoformat(),
                    studies=studies, exported=len(reports))
        self.snapshot = (('window.RESULTS = '+json.dumps(data)+';\n').encode(), frozenset(), registry)


def allowed(peer, networks):
    try:
        address = ipaddress.ip_address(peer)
        if getattr(address, 'ipv4_mapped', None):
            address = address.ipv4_mapped
        return any(address in network for network in networks)
    except ValueError:
        return False


def byte_range(value, size):
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
    if not match or not any(match.groups()) or size == 0:
        raise ValueError('Invalid range')
    left, right = match.groups()
    if left:
        start, end = int(left), min(int(right), size-1) if right else size-1
    else:
        if int(right) == 0:
            raise ValueError('Invalid suffix')
        start, end = max(0, size-int(right)), size-1
    if start >= size or start > end:
        raise ValueError('Unsatisfiable range')
    return start, end


def handler(catalog, networks):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'OmicsExplorer/1'

        def end_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'same-origin')
            super().end_headers()

        def payload(self, body, mime):
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            # Trust the TCP peer only, never caller-controlled forwarding headers.
            if not allowed(self.client_address[0], networks):
                self.send_error(403, 'Network not allowed')
                return
            name = unquote(urlsplit(self.path).path)
            if name == '/':
                self.send_response(302)
                self.send_header('Location', '/results/')
                self.end_headers()
                return
            if not name.startswith('/results/'):
                self.send_error(404)
                return
            name = name[len('/results/'):]
            try:
                if name == 'catalog.js':
                    self.payload(catalog.snapshot[0], 'text/javascript; charset=utf-8')
                elif name in ('', 'index.html', 'style.css', 'theme.css', 'app.js', 'nav.js', 'nav.css', 'favicon.svg'):
                    path = STATIC/(name or 'index.html')
                    self.payload(path.read_bytes(), mimetypes.guess_type(path)[0]+'; charset=utf-8')
                elif name.startswith('reports/'):
                    registry = catalog.snapshot[2]
                    route = name[len('reports/'):]
                    path = resolve(catalog.base, registry, route)
                    key = route.split('/', 1)[0]
                    canonical = key+'/'+path.relative_to(catalog.base/registry[key]).as_posix()
                    if route != canonical:
                        # Preserve ?d=2, used by nested gene pages for navigation.
                        query = urlsplit(self.path).query
                        location = '/results/reports/'+quote(canonical, safe='/')
                        if query:
                            location += '?'+query
                        self.send_response(302)
                        self.send_header('Location', location)
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                    else:
                        relative = path.relative_to(catalog.base/registry[key]).as_posix()
                        if relative == 'assets/js/main.js':
                            self.payload(report_script(path.read_text()).encode('utf-8'), 'text/javascript; charset=utf-8')
                        elif relative == 'assets/css/main.css':
                            self.payload(report_css(path.read_text()).encode('utf-8'), 'text/css; charset=utf-8')
                        elif path.suffix.lower() in ('.html', '.htm'):
                            self.payload(report_html(path.read_text(), relative).encode('utf-8'), 'text/html; charset=utf-8')
                        else:
                            self.stream(path)
                else:
                    self.send_error(404)
            except (FileNotFoundError, PermissionError, ValueError):
                self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def stream(self, path):
            with path.open('rb') as f:
                import os
                size = os.fstat(f.fileno()).st_size
                start, end = 0, size-1
                partial = self.headers.get('Range')
                if partial:
                    try:
                        start, end = byte_range(partial, size)
                    except ValueError:
                        self.send_response(416)
                        self.send_header('Content-Range', f'bytes */{size}')
                        self.send_header('Content-Length', '0')
                        self.end_headers()
                        return
                self.send_response(206 if partial else 200)
                self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(end-start+1))
                self.send_header('Accept-Ranges', 'bytes')
                if partial:
                    self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.end_headers()
                if self.command != 'HEAD':
                    f.seek(start)
                    remaining = end-start+1
                    while remaining > 0:
                        chunk = f.read(min(256*1024, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Local config with explicit external report folders')
    parser.add_argument('--check-config', action='store_true', help='Validate mounts and exit without opening a socket')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8002)
    parser.add_argument('--allow-cidr', action='append', default=[], help='Repeat for campus and VPN networks')
    parser.add_argument('--refresh-seconds', type=int, default=300)
    args = parser.parse_args()
    if args.host not in ('127.0.0.1', 'localhost', '::1') and not args.allow_cidr:
        parser.error('LAN binding requires explicit --allow-cidr for campus/VPN networks')
    if args.refresh_seconds < 30:
        parser.error('Refresh interval must be at least 30 seconds')
    try:
        networks = [ipaddress.ip_network(n) for n in ['127.0.0.0/8', '::1/128']+args.allow_cidr]
    except ValueError as e:
        parser.error(str(e))
    catalog = Catalog(args.config)
    try:
        catalog.refresh()
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if args.check_config:
        print(f'Config OK: {len(catalog.snapshot[2])} report(s).')
        return
    server = ThreadingHTTPServer((args.host, args.port), handler(catalog, networks))
    stop = threading.Event()
    def refresh_loop():
        while not stop.wait(args.refresh_seconds):
            try:
                catalog.refresh()
            except Exception:
                logging.exception('Refresh failed; retaining previous catalog')
    threading.Thread(target=refresh_loop, daemon=True).start()
    print(f'Listening on http://{args.host}:{args.port}/results/ (allowed peers: {", ".join(map(str, networks))})', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()

if __name__ == '__main__':
    main()
