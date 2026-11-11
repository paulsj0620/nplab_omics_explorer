# omics_explorer

Read-only website shell for opening existing omics HTML reports. Includes a searchable report list, neutral glass interface, and click, keyboard and drag navigation. No research data, analysis reports, pipelines, result images, gene tables, databases or credentials are included.

## Run

Requires Python 3.10+. The server uses only the standard library.

```bash
python3 server.py
```

Open **http://127.0.0.1:8002/results/**. With no configuration, the shell opens with an empty report list. It does not scan your machine for data.

To connect your own reports, copy `config.example.json` to `config.local.json` (ignored by Git) and add explicit report directories:

```json
{
  "reports": [
    {
      "id": "example-study",
      "name": "Example study",
      "kind": "rnaseq",
      "path": "/path/to/external/report",
      "entry": "home/index.html"
    }
  ]
}
```

This is a configuration illustration, not included analysis data. `kind` may be `rnaseq`, `scrnaseq` or another label; other labels remain visible under All reports. Paths can be absolute or relative to the configuration file. Each ID must be unique. Without `entry`, the server tries `index.html` then `home/index.html`. Symlinks and path traversal are rejected. Keep datasets outside this source directory.

```bash
python3 server.py --config config.local.json --check-config
python3 server.py --config config.local.json
```

The catalog refreshes every 300 seconds; reload the browser to see the latest list. If refresh fails, the previous valid catalog remains. Absolute mount paths are not sent to the browser. Files are read from explicitly mounted report directories, never copied into the repository.

## Remote access

Run the server on the machine holding the reports. From your own computer, open a separate terminal:

```bash
ssh -4 -N -L 127.0.0.1:18002:127.0.0.1:8002 USER@HOST
```

Then visit **http://127.0.0.1:18002/results/**. Keep both the server and tunnel running.

Direct LAN service requires explicit network ranges, for example `--host 0.0.0.0 --allow-cidr YOUR_NETWORK_CIDR`. There is no built-in login. The server checks the TCP peer; it ignores forwarding headers. If placed behind a proxy, access restrictions must also be applied at that proxy. Do not infer campus-wide access from an SSH connection.

## Report presentation and navigation

- `static/theme.css` styles both the portal and mounted reports; it does not rewrite source files or scientific figures.
- `presentation.py` removes known legacy vendor header/footer branding from responses. Generic report scripts are served unchanged. No replacement logo or footer branding is added.
- Mixed-case paths are redirected to the actual report filename when the match is unambiguous. Query strings such as `?d=2` are preserved.
- Top navigation uses one selected pill with a 260 ms transition. Drag starts after 6 px, previews without navigation, and invokes the original button/link on release. Escape, pointer cancellation, leaving the allowed area, resize and blur cancel a drag. Modified link clicks and keyboard activation retain normal behavior. Reduced motion disables animation.
- Mounted reports with the existing `.menu_item_box > a` structure get navigation automatically. Custom report navigation can opt in with `data-drag-nav` on a container of direct child buttons or links.
- Browser tests use synthetic markup only. Real report integrity and access policy remain the report owner's responsibility.

## Checks

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/nav.test.cjs
node --check static/nav.js
python3 scripts/check_release.py
```

The prepared source passes 9 Python tests and 6 Node interaction tests. These cover request routing, read-only report mounts, path/network boundaries, response transforms, and navigation state. They do not verify browser rendering.

An optional Playwright browser spec is provided in `tests/browser.spec.cjs` for viewport, interaction and screenshot checks. With `@playwright/test` and Chromium installed in the developer's own environment, run `npx playwright test tests/browser.spec.cjs`. No report data or running server is required. Review the screenshots in the ignored `test-results/` folder. Production-browser visual verification has not been performed in the restricted authoring environment.

## Publish the source

`.gitignore` allows only the application source, tests and documentation. `scripts/check_release.py` checks the exact tracked file list, verifies staged and working content match, and rejects unexpected paths, oversized files and known credential/private-path markers. Review the staged diff as well; marker checks cannot identify every possible secret or dataset. It can create a ZIP from those tracked files; it never recursively archives the working directory.

```bash
git init -b main
git add .
python3 scripts/check_release.py --archive ../omics_explorer-source.zip
git commit -m "Initial omics_explorer web shell"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

No GitHub repository is created or published by starting this application. Do not add analysis outputs, report directories or local configurations to the allowlist.
