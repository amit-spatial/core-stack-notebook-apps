# marimo Learnings

This file captures practical setup lessons from the first CoRE Stack marimo deployment.

## What Worked

- `marimo export html-wasm` is the right GitHub Pages target for a static, interactive notebook app.
- GitHub Pages deployment works cleanly with the official Pages Actions flow:
  - `Settings -> Pages -> Build and deployment -> Source -> GitHub Actions`
  - `Actions -> All workflows -> Deploy GitHub Pages -> Run workflow`
- After Pages is configured, the workflow can redeploy automatically on push.
- `uv sync --frozen --extra dev` is a good CI install command because it catches lockfile drift.
- `marimo check` should run before export.
- `ruff` can lint marimo notebooks, but notebook files need `B018` ignored because marimo intentionally uses final expressions for display.

## GitHub Pages Pattern

```bash
uv run marimo check notebooks/01_public_data_browser.py
uv run marimo export html-wasm notebooks/01_public_data_browser.py \
  --output site \
  --mode run \
  --no-show-code
python -m http.server --directory site 8000
```

The exported app must be served over HTTP. Opening `site/index.html` through `file://` is not enough.

## WASM Pattern

For deployable notebooks:

- keep the notebook self-contained or use packages available in the browser runtime
- list dependencies in the PEP 723 script block
- avoid depending on local `src/` imports unless packaging/loading them for WASM is explicitly handled
- do not rely on `.env` in the browser
- collect credentials through UI elements instead of embedding secrets
- use `mo.stop(..., output)` to halt downstream cells gracefully
- catch expected network/API failures and render callouts instead of letting dependent cells show ancestor errors

## CORS Lesson

Static GitHub Pages apps run API calls in the user's browser. Browser CORS rules apply even when the API key is valid.

For the CoRE Stack public API, the backend needs to allow:

- origin: `https://amit-spatial.github.io`
- header: `X-API-Key`
- methods: `GET`, `OPTIONS`

The current backend settings already include `X-API-Key` in `CORS_ALLOW_HEADERS`, but production must set `CORS_ALLOWED_ORIGINS` to include the GitHub Pages origin.

## User Experience Pattern

Before credentials are entered, a notebook should still show:

- what the app will unlock
- why the analysis matters
- where to get an API key
- the broad flow of the app
- sample outputs or placeholders when appropriate

For this project, always link to https://dashboard.core-stack.org/ when asking for a CoRE Stack API key.

## References To Recheck

- marimo docs: https://docs.marimo.io/
- WASM export: https://docs.marimo.io/guides/exporting/webassembly_html/
- GitHub Pages publishing: https://docs.marimo.io/guides/publishing/github/
- marimo examples: https://github.com/marimo-team/marimo/tree/main/examples
- awesome-marimo libraries: https://github.com/marimo-team/awesome-marimo
- marimo AI skills: https://docs.marimo.io/guides/generate_with_ai/skills/

