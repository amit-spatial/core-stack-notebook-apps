# Architecture

This repo should behave like a small app suite, not a folder of disconnected notebooks.

## Design Principles

1. Keep notebook files as composition layers.
   API calls, normalization, and GeoJSON utilities belong in `src/corestack_notebook_apps/`.

2. Use administrative geography for discovery, but watershed `uid` for analysis.
   CoRE Stack users usually start with state, district, and tehsil names; joins should converge on MWS identifiers.

3. Treat public APIs and STAC as complementary surfaces.
   Public APIs are task-oriented and app-friendly. STAC is asset-oriented and metadata-rich.

4. Prefer reactive controls over callback code.
   marimo will rerun dependent cells when a selected geography or MWS changes.

5. Keep exports in mind from the first notebook.
   A useful notebook should run as a marimo app, execute as a script, and be eligible for docs embedding later.

## App Flow

```text
active locations
  -> selected state/district/tehsil
  -> layer catalog
  -> MWS + village geometries
  -> selected MWS uid
  -> MWS time series + KYL row + report link
```

## Public Data Surfaces

The first app uses these routes:

- `GET /api/v1/get_active_locations/`
- `GET /api/v1/get_generated_layer_urls/`
- `GET /api/v1/get_mws_geometries/`
- `GET /api/v1/get_village_geometries/`
- `GET /api/v1/get_mws_data/`
- `GET /api/v1/get_mws_kyl_indicators/`
- `GET /api/v1/get_mws_report/`

The live probe on 2026-05-17 confirmed that `Andhra Pradesh / Ananthapur / Amadagur` returns:

- 22 active states
- 70 generated layer records for the sample tehsil
- 44 MWS geometries
- 15 village geometries
- 209 time-series rows for sample MWS `3_3972`

