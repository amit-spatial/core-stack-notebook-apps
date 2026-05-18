# GitHub Pages Deployment

This repo deploys the marimo notebook suite as WebAssembly HTML exports.

## Workflow

The GitHub Actions workflow at `.github/workflows/pages.yml` runs on pushes to `dev` or `main`, and on manual dispatch.

It:

1. installs dependencies with `uv`
2. lints `src/`, `notebooks/`, and `scripts/`
3. validates each notebook with `marimo check`
4. exports each notebook with `marimo export html-wasm`
5. uploads the generated `site/` directory as the GitHub Pages artifact

## Repository Settings

In GitHub, set Pages to use **GitHub Actions** as the source:

`Settings -> Pages -> Build and deployment -> Source -> GitHub Actions`

The first deployment may need to be kicked manually:

`Actions -> All workflows -> Deploy GitHub Pages -> Run workflow`

After this, pushes to `dev` or `main` redeploy automatically.

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

For the current Django backend, this means setting `CORS_ALLOWED_ORIGINS` in production to include the Pages origin. `X-API-Key` is already present in `CORS_ALLOW_HEADERS` in `nrm_app/settings.py`.

## Local Export

```bash
uv run python scripts/build_pages.py
uv run python -m http.server --directory site 8010
```

Use port `8010` by default for local previews. If it is already in use, choose the next
free port and keep the `site/` directory the same.

The root `site/index.html` links to:

- `/public-data-browser/`
- `/exploratory-layer-studio/`
- `/mws-deep-dive/`

## Template Reference

The repo https://github.com/amit-spatial/marimo-gh-pages-template is a useful reference
when this deployment needs to become more generic.

It demonstrates:

- exporting app files from `apps/` in run mode
- exporting notebook files from `notebooks/` in edit mode
- generating the root index through Jinja templates
- keeping notebook-local assets in `public/`

This project currently keeps all deployable experiences as run-mode apps, so
`scripts/build_pages.py` is intentionally simpler. The template can still guide a future
split between public apps, editable notebooks, reusable templates, and static assets.
