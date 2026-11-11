# omics_explorer

Read-only portal for browsing RNA-seq and single-cell HTML reports. This repository contains the website source only; reports and analysis data stay outside it.

## Run

Requires Python 3.10+, with no additional packages.

```bash
python3 server.py
```

Open **http://127.0.0.1:8002/results/**. The report list is empty until configured.

## Connect reports

Copy `config.example.json` to `config.local.json` (ignored by Git) and add your report folders:

```json
{
  "reports": [{
    "id": "example",
    "name": "Example study",
    "kind": "rnaseq",
    "path": "/path/to/report",
    "entry": "home/index.html"
  }]
}
```

Use unique IDs. `kind` selects the `rnaseq` or `scrnaseq` filter. Paths can be absolute or relative to the configuration file. Original report files are read without modification.

```bash
python3 server.py --config config.local.json
```

## Remote access

Keep the server running on the report host. From your computer:

```bash
ssh -4 -N -L 127.0.0.1:18002:127.0.0.1:8002 USER@HOST
```

Visit **http://127.0.0.1:18002/results/** while the tunnel is running.

There is no built-in login. Keep the default localhost binding and use an SSH tunnel; do not expose the server directly to the internet. Mount only trusted report folders, since allowed file types anywhere inside them can be downloaded.

## Development

```bash
python3 -B -m unittest discover -s tests
node --test tests/nav.test.cjs
```

Before pushing, stage changes and run `python3 scripts/check_release.py` to check the source allowlist and known secret markers. Browser visual verification is still pending; development guidelines are in [AGENTS.md](AGENTS.md).
