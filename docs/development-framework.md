# Development Framework

The repo should grow as a suite of marimo-native, research-grade geospatial apps for CoRE Stack.
The goal is not only to show public data. The goal is to help people use that data:
combine outputs, draw defensible inferences, compare places, plan action, and learn how
to move from map evidence to field decisions.

marimo is especially valuable here because one notebook can be a guided app, an
explainable analysis, a reproducible script, and a deployable web experience at the same
time.

## Product Principle

Every app should answer at least one of these questions:

- What is here?
- Why does it matter?
- What does the evidence suggest?
- What should be checked next?
- What action options become visible from this combination of signals?
- What can a user export, reuse, or discuss with others?

Data display is only the first layer. A strong notebook should turn CoRE Stack API output
into a guided reasoning flow.

## App Families

- Discovery apps: help users see what data exists, where it exists, and how to fetch it.
- Exploratory apps: let users compare layers, query geographies, rank watersheds, and export early findings.
- Deep-dive apps: explain methods, code, assumptions, and analytical logic while producing reusable outputs.
- Geospatial stories: combine narrative, maps, charts, code snippets, and place-based interpretation in the spirit of ArcGIS StoryMaps, but implemented as reactive marimo notebooks.
- Action planning apps: combine geospatial signals into prioritization, intervention menus, risk flags, and field-check lists.
- Guided tour apps: walk users through maps, widgets, evidence layers, tooltips, and interpretation steps one decision at a time.
- Utility dashboards: let users compose their own panels, metrics, filters, maps, rankings, and export tables from API-backed data.
- Research demos: test libraries such as TorchGeo, EVoC, Tessera, DuckDB, lonboard, geopandas, rasterio, pystac, and cloud-native geospatial formats.

## App Experience Modes

Apps can expose several modes without becoming separate projects:

- Guided mode: a step-by-step path with callouts, map annotations, and suggested clicks.
- Explore mode: free filtering, map panning, layer toggles, comparison charts, and search.
- Planner mode: ranking, threshold sliders, weighted scoring, intervention options, and notes.
- Research mode: visible code snippets, method assumptions, uncertainty, and exportable tables.
- Story mode: place-based narrative with bookmarks, map states, and evidence panels.

The same backend data can power all of these modes. marimo's reactivity makes the
transition from one mode to another cheap: controls change, derived cells recompute, and
maps/charts update without rebuilding the app.

## Inference Patterns

Notebooks should combine multiple API outputs into higher-value signals. Useful patterns:

- Layer plus boundary: use generated layer URLs with MWS/village geometries to explain where a layer applies.
- Time series plus indicators: connect water balance trends to KYL indicator categories.
- Map plus rank table: let users click a place, then see why it ranks high or low.
- Signal plus action menu: translate evidence into possible field checks or intervention families.
- Before/after or scenario comparison: let users change thresholds, weights, seasons, or selected layers and watch the result update.
- Exportable reasoning trail: include the selected geography, filters, scores, caveats, and source URLs in a table users can download or copy.

Example action-planning logic:

```python
priority_score = (
    0.35 * normalized_water_stress
    + 0.25 * normalized_runoff_pressure
    + 0.20 * normalized_restoration_area
    + 0.20 * normalized_village_exposure
)
```

The exact formula can change by audience, but every formula should show inputs,
weights, interpretation, and caveats.

## Guided Interaction Standards

Every substantial app should help users understand what to do next:

- start with a visible framework before API keys are entered
- use callouts to explain why a control matters
- put map tooltips on important layers, especially MWS uid, village name, dataset name, and indicator values
- include a short "try this" prompt beside complex widgets
- make defaults meaningful so the first loaded view already teaches something
- use tabs or sections for progressive steps instead of one overwhelming wall of outputs
- keep one-click reset or "start over" paths for guided tours
- show code snippets where they help users adapt the workflow outside the app

For maps, prefer interactions that teach spatial reasoning:

- auto-zoom to selected geometry
- show selected and neighboring features with different styles
- include layer legends and clear labels
- use hover/click tooltips for "what is this?" moments
- pair the map with a table or chart that explains the selected feature
- keep a visible source or API endpoint reference for the active layer

## Dashboard Composition

Utility dashboards should let users assemble views from API-backed pieces:

- metric cards for selected geography
- map panel with active layer toggles
- ranking table for watersheds, villages, or assets
- chart panel for time series and distributions
- inspector panel for selected feature metadata
- export panel for CSV, JSON manifest, or report URLs

Possible widget families:

- geography selectors: state, district, tehsil, MWS, village
- layer selectors: dataset, type, version, search term
- threshold sliders: stress, runoff, slope, tree-cover change, cropping intensity
- weight sliders: let planners change score importance interactively
- scenario toggles: drought focus, restoration focus, surface-water focus, cropping focus
- download/copy controls: manifest, selected rows, summary markdown, report link

The dashboard should not only summarize metrics; it should let users ask "what happens
if this criterion matters more?" and immediately see how maps and rankings change.

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
- show map/tool/chart guidance before asking users to interpret outputs
- include at least one inference, ranking, scenario, or action-planning component when possible
- include reusable code snippets for researchers and developers
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

4. `05_action_planner.py`
   - combine MWS, village, layer inventory, and KYL indicators
   - expose sliders for priority scoring weights
   - rank candidate micro-watersheds
   - show recommended field checks and possible intervention families
   - export a planning brief

5. `06_guided_map_tour.py`
   - teach users how to read CoRE Stack maps step by step
   - highlight one layer at a time
   - use tooltips, callouts, and map bookmarks
   - ask users to try controls and observe how outputs change
   - end with a small self-arranged dashboard

## Deployment Standard

The current workflow deploys a generated static index with cards linking to exported
notebook apps. As more apps are added, keep the index organized by app family and
audience.

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
