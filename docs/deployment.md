# GitHub Pages Deployment

This repo deploys the marimo app as a WebAssembly HTML export.

## Workflow

The GitHub Actions workflow at `.github/workflows/pages.yml` runs on pushes to `main` and on manual dispatch.

It:

1. installs dependencies with `uv`
2. validates the notebook with `marimo check`
3. lints `src/` and `notebooks/`
4. exports `notebooks/01_public_data_browser.py` with `marimo export html-wasm`
5. uploads the generated `site/` directory as the GitHub Pages artifact

## Repository Settings

In GitHub, set Pages to use **GitHub Actions** as the source:

`Settings -> Pages -> Build and deployment -> Source -> GitHub Actions`

## Credentials

GitHub Pages is static, so the app must not contain the private CoRE Stack API key.
Users paste their API key into the app at runtime. The key stays in their browser session and is not committed or stored by this repo.

## CORS Requirement

Because the exported app runs in the user's browser, the CoRE Stack API must allow browser requests from the GitHub Pages origin.

The public API currently responds to an `OPTIONS` preflight, but does not include `Access-Control-Allow-Origin` or `Access-Control-Allow-Headers` for `X-API-Key`. If that remains true in production, the GitHub Pages app will load but browser requests to the API will be blocked before they reach Django.

Fix this by allowing the deployed Pages origin, for example:

- `https://amit-spatial.github.io`
- the final custom docs/webapps origin, once chosen

The backend also needs to allow the `X-API-Key` request header for public API routes.

## Local Export

```bash
rm -rf site
uv run marimo export html-wasm notebooks/01_public_data_browser.py \
  --output site \
  --mode run \
  --no-show-code
python -m http.server --directory site 8000
```
