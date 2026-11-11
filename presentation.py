"""Presentation-only changes for served reports; original report files stay intact."""
import re

FAVICON = '<link rel="icon" type="image/svg+xml" href="/results/favicon.svg?v=2">'
THEME = ('<link rel="stylesheet" href="/results/theme.css?v=20261111-nav-1">'
         '<link rel="stylesheet" href="/results/nav.css?v=20261111-nav-1">'
         '<script defer src="/results/nav.js?v=20261111-nav-1"></script>')
FOOTER = 'function make_footer(depth) {}'


def report_script(text):
    text, count = re.subn(r'function make_footer\(depth\)\s*\{.*?\n\}',
                          lambda _: FOOTER, text, flags=re.S)
    if count == 0:
        return text  # Generic reports need no vendor-specific script changes.
    text = re.sub(r'<img\b[^>]*Theragen[^>]*>',
                  '', text, flags=re.I)
    text = re.sub(r':\s*Theragen\s+Bio|Theragen\s+Bio', '', text, flags=re.I)
    return text


def report_html(text, relative):
    # These are presentation/contact links, not scientific references or data.
    text = re.sub(r'\[?\s*<a\b[^>]*href=[\"\'][^\"\']*theragenbio\.com[^\"\']*[\"\'][^>]*>.*?</a>\s*\]?',
                  '', text, flags=re.I | re.S)
    text = re.sub(r'<img\b[^>]*Theragen[^>]*>', '', text, flags=re.I)
    text = re.sub(r'<link\b(?=[^>]*\brel=[\"\'][^\"\']*icon\b)[^>]*>', '', text, flags=re.I)
    text = re.sub(r':\s*Theragen\s+Bio|Theragen\s+Bio', '', text, flags=re.I)
    if relative == 'genes/index.html':
        # A delivered report uses the nested-page prefix in its overview page.
        text = text.replace('href="../../expression/', 'href="../expression/')
    text = re.sub(r'</head\s*>', lambda _: FAVICON+'</head>', text, count=1, flags=re.I)
    # The report JS appends vendor styles to <head> on DOM ready. Keeping this
    # link after the body content ensures our overrides stay last in document
    # order, even after those dynamically inserted stylesheets arrive.
    return re.sub(r'</body\s*>', lambda _: THEME+'</body>', text, count=1, flags=re.I)


def report_css(text):
    return text
