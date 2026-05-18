from __future__ import annotations

import html
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"


@dataclass(frozen=True)
class MarimoApp:
    notebook: str
    slug: str
    title: str
    description: str


APPS = (
    MarimoApp(
        notebook="notebooks/01_public_data_browser.py",
        slug="public-data-browser",
        title="Public Data Browser",
        description="Browse active locations, generated layers, MWS geometries, and KYL tables.",
    ),
    MarimoApp(
        notebook="notebooks/02_exploratory_layer_studio.py",
        slug="exploratory-layer-studio",
        title="Exploratory Layer Studio",
        description="Filter layer catalogs, inspect URLs, and build reusable layer manifests.",
    ),
    MarimoApp(
        notebook="notebooks/03_mws_deep_dive.py",
        slug="mws-deep-dive",
        title="MWS Deep Dive",
        description="Turn one micro-watershed into a compact analytical brief.",
    ),
)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def write_index() -> None:
    cards = "\n".join(
        f"""
        <article class="app-card">
          <p class="eyebrow">marimo app</p>
          <h2>{html.escape(app.title)}</h2>
          <p>{html.escape(app.description)}</p>
          <a href="{html.escape(app.slug)}/">Open app</a>
        </article>
        """
        for app in APPS
    )
    index = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CoRE Stack Notebook Apps</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5e6b78;
      --line: #d8e0e6;
      --paper: #f7faf9;
      --accent: #0f766e;
      --accent-dark: #134e4a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family:
        Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header {{
      padding: 56px clamp(20px, 5vw, 72px) 32px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    main {{
      width: min(1120px, calc(100% - 40px));
      margin: 36px auto 56px;
    }}
    h1 {{
      max-width: 860px;
      margin: 0;
      font-size: clamp(2rem, 6vw, 4rem);
      line-height: 1;
      font-weight: 760;
    }}
    .lede {{
      max-width: 800px;
      margin: 20px 0 0;
      color: var(--muted);
      font-size: 1.1rem;
      line-height: 1.65;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
    }}
    .app-card {{
      min-height: 260px;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      display: flex;
      flex-direction: column;
    }}
    .eyebrow {{
      margin: 0 0 28px;
      color: var(--accent);
      font-size: 0.76rem;
      font-weight: 760;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 0;
      font-size: 1.45rem;
      line-height: 1.2;
    }}
    .app-card p:not(.eyebrow) {{
      color: var(--muted);
      line-height: 1.55;
    }}
    a {{
      margin-top: auto;
      color: #ffffff;
      background: var(--accent);
      border-radius: 6px;
      padding: 10px 14px;
      text-decoration: none;
      width: fit-content;
      font-weight: 720;
    }}
    a:hover {{ background: var(--accent-dark); }}
    footer {{
      width: min(1120px, calc(100% - 40px));
      margin: 0 auto 40px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>CoRE Stack Notebook Apps</h1>
    <p class="lede">
      A deployable marimo suite for exploring public CoRE Stack geospatial data,
      from discovery to watershed-level analysis.
    </p>
  </header>
  <main>
    <section class="grid">
      {cards}
    </section>
  </main>
  <footer>
    Static GitHub Pages build. API-backed apps ask for a CoRE Stack key at runtime.
  </footer>
</body>
</html>
"""
    (SITE_DIR / "index.html").write_text(index, encoding="utf-8")


def main() -> None:
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    for app in APPS:
        run(["uv", "run", "marimo", "check", app.notebook])
        run(
            [
                "uv",
                "run",
                "marimo",
                "export",
                "html-wasm",
                app.notebook,
                "--output",
                str(SITE_DIR / app.slug),
                "--mode",
                "run",
                "--no-show-code",
            ]
        )

    write_index()
    (SITE_DIR / ".nojekyll").touch()


if __name__ == "__main__":
    main()
