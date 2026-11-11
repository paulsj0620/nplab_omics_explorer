# omics_explorer

This repository contains the website shell only. Never commit report data, analytical results, images, exports, databases, local report mounts, credentials or deployment secrets. Use the exact source allowlist in `.gitignore`; verify tracked files before publication. Do not copy reports or third-party template assets into this repository. Tests use synthetic fixtures in temporary directories.

Source report content is read-only. Make presentation changes in the response layer or `static/theme.css`. Preserve data, figure colors, units, links, query strings, read-only access checks and range downloads. Never add logos or footer branding without a new user instruction.

## Current visual rules

- White/neutral gray glass-inspired interface; Arial, Apple SD Gothic Neo, sans-serif, body 14px/1.55. Glass is for controls/navigation; graphs remain opaque white.
- Panel/table outer radius 24px; inset blocks 16px; general fields 14px; buttons/top single-line fields/nav 999px; grouped menus/dialogs 28px.
- Groups: padding/gap 8px, min-height 58px. Top nav: padding/gap 4px, buttons 36px high, padding 0 12px, font weight 700. Main actions: 40px high, 12px font, weight 700.
- Active #292b2e/white; fields #bac2ca with inset shadow; group/nav border #8997a5; cards #c0c7ce or rgba(100,110,120,.20).
- Menu shadow: inset 0 1px 0 #fff, inset 0 -1px 0 #ffffffa6, 0 2px 4px #28344130, 0 8px 18px #28344120. Group blur 22px/saturate 125%; large controls 24px/125%; header 28px/130%, with webkit fallback.
- Use the existing fixed neutral radial/linear background. Work controls first, compact status, then content. Duplicate headings are sr-only. Do not add marketing intros.
- Menus wrap with overflow visible. Scroll tables/images/settings internally; do not clip parent shadows. body min-width 0; html scrollbar-gutter stable. Preserve focus-visible and reduced-motion/transparency settings.
- Click/keyboard selection: one indicator, 260ms cubic-bezier(.22,1,.36,1), no content sliding. Drag threshold 6px, delayed pointer capture, preview only until release, then existing click handler. Out-of-bounds release, Esc, cancel, lost capture, blur and resize cancel. Suppress only the generated trusted pointer click, not keyboard/programmatic activation. Observe real geometry, ignore decoration mutations, keep hidden/disabled items out of targets.

## Verification

Run Python boundary/config/HTTP tests and Node navigation tests. Check browser states at 1920x1080, a lower-height desktop viewport, widths 1280/1100/600, and inspect screenshots. Keep the inability to run a browser explicit; parser/unit checks do not count as visual verification. Browser QA must not use production data or execute write APIs. Version CSS/JS query parameters when changing assets. Include new static assets in server routing and release allowlist.

Current verification status is recorded in README and task handoff. No automatic GitHub push, data import or deployment occurs as part of starting the shell.
