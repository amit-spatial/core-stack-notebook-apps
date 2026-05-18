# CoRE Stack Notebook Apps

marimo-native notebooks and deployable web apps for exploring CoRE Stack public geospatial data.

This repo is being rebuilt around the current CoRE Stack public surface:

- discover active geographies through `GET /api/v1/get_active_locations/`
- inspect generated vector and raster layers through `GET /api/v1/get_generated_layer_urls/`
- fetch stable MWS and village geometries
- join analytical tables through the watershed `uid`
- expose the workflow as reproducible marimo notebooks, scripts, and app views

## Why marimo

marimo notebooks are Python files, reactive apps, and executable scripts at the same time. That matters here because CoRE Stack analysis wants all three:

- a contributor can edit notebooks as normal Python
- a user can run the notebook as an app without seeing implementation code
- the same file can be checked, tested, exported, and embedded in docs

## Current Shape

```text
.
├── notebooks/
│   └── 01_public_data_browser.py
├── src/corestack_notebook_apps/
│   ├── config.py
│   ├── geo.py
│   └── public_api.py
├── docs/
│   └── architecture.md
└── .archive/
    ├── README.md
    └── legacy-2026-05-17/
```

## Quickstart

Use `uv` for everything.

```bash
uv sync
uv run marimo run notebooks/01_public_data_browser.py
```

For editing:

```bash
uv run marimo edit --watch notebooks/01_public_data_browser.py
```

For validation:

```bash
uv run marimo check notebooks/01_public_data_browser.py
uv run notebooks/01_public_data_browser.py
```

## API Credentials

The app reads credentials from `.env` without displaying them in the notebook.

Preferred key:

```dotenv
PUBLIC_API_X_API_KEY=...
```

The current local `.env` also has the legacy key name `corestsack-api-key`, which is supported for compatibility.

## First App

`notebooks/01_public_data_browser.py` is the seed app. It lets a user:

- choose an active state, district, and tehsil
- inspect published layer inventory by dataset and layer type
- load MWS and village geometries
- preview those geometries on a lightweight map
- select one MWS and fetch its time series plus KYL indicator row

This is intentionally the narrow waist of the repo. Future notebooks should reuse `src/corestack_notebook_apps/` instead of copying request or GeoJSON logic.

## Deploy To GitHub Pages

The repo is configured to deploy the first app as a marimo WebAssembly export through GitHub Actions.

In GitHub, set Pages to use GitHub Actions:

`Settings -> Pages -> Build and deployment -> Source -> GitHub Actions`

Then push to `dev` or `main`, or run the `Deploy GitHub Pages` workflow manually.

GitHub Pages is static, so the public app does not include a private API key. Users paste their CoRE Stack API key into the app at runtime.

See [docs/deployment.md](docs/deployment.md) for the workflow details.

## Archive

The previous exploratory files are preserved under `.archive/legacy-2026-05-17/`.
See [.archive/README.md](.archive/README.md) for a map of what moved and when to use it.

## References

- CoRE Stack docs: https://docs.core-stack.org/
- CoRE Stack public APIs: https://docs.core-stack.org/use-precomputed-data/public-apis/
- CoRE Stack STAC docs: https://docs.core-stack.org/use-precomputed-data/stac-specs/
- marimo docs: https://docs.marimo.io/
