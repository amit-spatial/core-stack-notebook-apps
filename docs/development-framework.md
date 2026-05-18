# Development Framework

The repo should grow as a suite of marimo-native, research-grade geospatial apps for CoRE Stack.

## App Families

- Discovery apps: help users see what data exists, where it exists, and how to fetch it.
- Exploratory apps: let users compare layers, query geographies, rank watersheds, and export early findings.
- Deep-dive apps: explain methods, code, assumptions, and analytical logic while producing reusable outputs.
- Geospatial stories: combine narrative, maps, charts, code snippets, and place-based interpretation in the spirit of ArcGIS StoryMaps, but implemented as reactive marimo notebooks.
- Research demos: test libraries such as TorchGeo, EVoC, Tessera, DuckDB, lonboard, geopandas, rasterio, pystac, and cloud-native geospatial formats.

## Audience Modes

Each app can later branch toward a different audience:

- researchers and data scientists: code, method notes, exports, uncertainty, reproducibility
- stewards and planners: place selection, priority ranking, intervention logic, printable summaries
- farm workers and local communities: simpler language, maps, visual explanations, offline-friendly exports
- developers: API calls, schemas, STAC assets, reusable snippets

## Notebook Standard

Every deployable notebook should:

- be a `.py` marimo notebook
- start with a PEP 723 dependency block
- show useful context before credentials are entered
- link to https://dashboard.core-stack.org/ for API keys
- use `mo.stop` for expected gating
- catch API/CORS failures and display callouts
- run with `uv run <notebook.py>`
- pass `uv run marimo check <notebook.py>`
- export with `uv run marimo export html-wasm ...`

## Suggested Next Notebooks

1. `02_exploratory_layer_studio.py`
   - active location browser
   - layer catalog filters
   - vector/raster download links
   - geometry preview
   - export selected layer manifest

2. `03_mws_deep_dive.py`
   - one watershed, many signals
   - water balance time series
   - KYL indicators
   - villages intersecting an MWS
   - method notes and code snippets beside charts

3. `04_place_story.py`
   - narrative sections
   - map bookmarks
   - before/after layer comparisons
   - local interpretation and recommended next questions

## Deployment Standard

The current workflow deploys the first app. As more apps are added, move toward a generated static index with cards linking to each exported notebook.

Possible structure:

```text
site/
  index.html
  public-data-browser/
  exploratory-layer-studio/
  mws-deep-dive/
  place-stories/
```

## Library Watchlist

- marimo for reactive notebook apps
- DuckDB and Polars for local analytics
- Altair, Plotly, lonboard, pydeck, folium for visualization
- geopandas, shapely, pyproj, rasterio, pystac for geospatial data
- TorchGeo for geospatial machine learning workflows
- EVoC for ecological/evolutionary computation experiments
- Tessera for large geospatial representation/model workflows as the stack matures
