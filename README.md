# R-PEAK Analytics Dashboard

Static browser-based analytics dashboard for R-PEAK project/task exports.

## Features

- Project setup analytics: start date → capacity and capability confirmation; green light → first patient.
- 150-day clinical trial target framing: 60-day setup and 30-day first-patient components.
- Project drill-down, task bottleneck views, thematic delayed-task analysis, and raw-data search.
- Browser-side CSV/XLS/XLSX upload with flexible column/sheet inference.
- Optional password-protected local server for public tunnel use.

## Local use

```bash
python3 src/build_dashboard.py
python3 -m http.server 8770 --bind 127.0.0.1 --directory public
```

## Protected serving

Do not commit real credentials. Set them via environment variables:

```bash
export RPEAK_DASH_USER=dashboard
export RPEAK_DASH_PASS='your-password-here'
python3 auth_server.py
```

Then expose with a tunnel if required, for example:

```bash
cloudflared tunnel --url http://127.0.0.1:8770
```

## Data

The bundled CSV is a public-safe synthetic demo dataset with 90 anonymised projects (`D0001`–`D0090`) and task patterns similar to the internal R-PEAK export. Do not commit real R-PEAK exports. Uploaded replacement datasets are parsed locally in the browser and stored in browser localStorage only.
