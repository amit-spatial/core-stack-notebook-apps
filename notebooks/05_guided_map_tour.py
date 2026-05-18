# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair>=5.5.0",
#     "folium>=0.19.0",
#     "httpx>=0.28.1",
#     "marimo[recommended]>=0.23.6",
#     "polars>=1.30.0",
# ]
# ///

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    from collections.abc import Iterable
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any

    import altair as alt
    import folium
    import httpx
    import marimo as mo
    import polars as pl

    DEFAULT_PUBLIC_API_BASE_URL = "https://geoserver.core-stack.org/api/v1"
    API_KEY_NAMES = (
        "PUBLIC_API_X_API_KEY",
        "CORESTACK_API_KEY",
        "CORE_STACK_API_KEY",
        "corestsack-api-key",
    )

    TOUR_STEPS = {
        "1. Orient to the landscape": {
            "kind": "info",
            "prompt": (
                "Start by reading the tehsil, village, and MWS boundaries. "
                "Do not interpret a layer before you know the geography frame."
            ),
        },
        "2. Choose a micro-watershed": {
            "kind": "neutral",
            "prompt": (
                "Pick one MWS. Watch how the map, time series, and indicator table "
                "become a linked profile."
            ),
        },
        "3. Read water and vegetation signals": {
            "kind": "info",
            "prompt": (
                "Compare precipitation, runoff, ET, and NDVI. Look for stress, response, "
                "and seasonal mismatch rather than single numbers."
            ),
        },
        "4. Ask what action this suggests": {
            "kind": "warn",
            "prompt": (
                "Use KYL indicators and layer availability to form hypotheses: recharge, "
                "restoration, crop resilience, surface-water management, or social planning."
            ),
        },
        "5. Assemble your dashboard": {
            "kind": "success",
            "prompt": (
                "Turn panels on and off. A good field-facing dashboard should show only "
                "the evidence needed for the next conversation."
            ),
        },
    }

    EVIDENCE_GROUPS = {
        "Water, runoff, and drought": [
            "water",
            "hydrology",
            "runoff",
            "drought",
            "swb",
            "stream",
            "drainage",
            "well",
            "pond",
        ],
        "Land use, crop, and vegetation": [
            "lulc",
            "crop",
            "cropping",
            "ndvi",
            "tree",
            "forest",
            "farm",
        ],
        "Restoration and terrain": [
            "restoration",
            "clart",
            "terrain",
            "slope",
            "catchment",
            "depression",
            "plantation",
        ],
        "Social, economic, and governance context": [
            "nrega",
            "facility",
            "csr",
            "green",
            "mining",
            "lcw",
            "aquifer",
            "soge",
        ],
    }

    INDICATOR_SETS = {
        "Water stress": [
            "avg_precipitation",
            "avg_runoff",
            "avg_number_dry_spell",
            "avg_wsr_ratio_kharif",
            "avg_wsr_ratio_rabi",
            "avg_wsr_ratio_zaid",
            "drought_category",
        ],
        "Restoration": [
            "area_protection",
            "area_wide_scale_restoration",
            "area_tree_on_slope",
            "area_shrubs_on_slope",
            "decrease_in_tree_cover",
            "increase_in_tree_cover",
        ],
        "Cropping": [
            "cropping_intensity_avg",
            "cropping_intensity_trend",
            "avg_single_cropped",
            "avg_double_cropped",
            "avg_triple_cropped",
            "area_crops_on_plain",
        ],
        "Planning context": [
            "mws_intersect_villages",
            "total_nrega_assets",
            "mws_intersect_swb",
            "terraincluster_id",
            "aquifer_class",
            "soge_class",
        ],
    }

    def read_env_file(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}

        values = {}
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    @dataclass(frozen=True)
    class CoreStackSettings:
        public_api_base_url: str = DEFAULT_PUBLIC_API_BASE_URL
        public_api_key: str | None = None

        @classmethod
        def from_env(cls, env_file: str | Path = ".env") -> "CoreStackSettings":
            file_values = read_env_file(Path(env_file))
            api_key = None
            for key_name in API_KEY_NAMES:
                api_key = os.environ.get(key_name) or file_values.get(key_name)
                if api_key:
                    break

            base_url = (
                os.environ.get("PUBLIC_API_BASE_URL")
                or file_values.get("PUBLIC_API_BASE_URL")
                or DEFAULT_PUBLIC_API_BASE_URL
            )
            return cls(public_api_base_url=base_url.rstrip("/"), public_api_key=api_key)

    class CoreStackPublicAPIError(RuntimeError):
        pass

    @dataclass(frozen=True)
    class CoreStackPublicClient:
        api_key: str
        base_url: str = DEFAULT_PUBLIC_API_BASE_URL
        timeout: float = 60.0

        def get(self, path: str, **params: str | int | float | bool | None) -> Any:
            clean_params = {key: value for key, value in params.items() if value is not None}
            url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
            headers = {"Accept": "application/json", "X-API-Key": self.api_key}

            try:
                response = httpx.get(
                    url,
                    params=clean_params,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:500]
                message = f"{exc.response.status_code} response from {url}: {detail}"
                raise CoreStackPublicAPIError(message) from exc
            except httpx.HTTPError as exc:
                message = f"Could not reach {url}: {exc}"
                raise CoreStackPublicAPIError(message) from exc
            except Exception as exc:
                message = f"Unexpected browser/API error while requesting {url}: {exc!r}"
                raise CoreStackPublicAPIError(message) from exc

            return response.json()

        def active_locations(self) -> list[dict[str, Any]]:
            payload = self.get("get_active_locations/")
            if not isinstance(payload, list):
                raise CoreStackPublicAPIError("Expected active locations to be a list.")
            return payload

        def generated_layer_urls(
            self,
            *,
            state: str,
            district: str,
            tehsil: str,
        ) -> list[dict[str, Any]]:
            payload = self.get(
                "get_generated_layer_urls/",
                state=state,
                district=district,
                tehsil=tehsil,
            )
            if not isinstance(payload, list):
                raise CoreStackPublicAPIError("Expected generated layer URLs to be a list.")
            return payload

        def mws_geometries(self, *, state: str, district: str, tehsil: str) -> dict[str, Any]:
            payload = self.get(
                "get_mws_geometries/",
                state=state,
                district=district,
                tehsil=tehsil,
            )
            if not isinstance(payload, dict):
                raise CoreStackPublicAPIError("Expected MWS geometries to be a GeoJSON object.")
            return payload

        def village_geometries(self, *, state: str, district: str, tehsil: str) -> dict[str, Any]:
            payload = self.get(
                "get_village_geometries/",
                state=state,
                district=district,
                tehsil=tehsil,
            )
            if not isinstance(payload, dict):
                raise CoreStackPublicAPIError(
                    "Expected village geometries to be a GeoJSON object."
                )
            return payload

        def mws_data(
            self,
            *,
            state: str,
            district: str,
            tehsil: str,
            mws_id: str,
        ) -> dict[str, Any]:
            payload = self.get(
                "get_mws_data/",
                state=state,
                district=district,
                tehsil=tehsil,
                mws_id=mws_id,
            )
            if not isinstance(payload, dict):
                raise CoreStackPublicAPIError("Expected MWS data to be a dictionary.")
            return payload

        def mws_kyl_indicators(
            self,
            *,
            state: str,
            district: str,
            tehsil: str,
            mws_id: str,
        ) -> list[dict[str, Any]]:
            payload = self.get(
                "get_mws_kyl_indicators/",
                state=state,
                district=district,
                tehsil=tehsil,
                mws_id=mws_id,
            )
            if not isinstance(payload, list):
                raise CoreStackPublicAPIError("Expected MWS KYL indicators to be a list.")
            return payload

        def mws_report(
            self,
            *,
            state: str,
            district: str,
            tehsil: str,
            mws_id: str,
        ) -> dict[str, Any]:
            payload = self.get(
                "get_mws_report/",
                state=state,
                district=district,
                tehsil=tehsil,
                mws_id=mws_id,
            )
            if not isinstance(payload, dict):
                raise CoreStackPublicAPIError("Expected MWS report response to be a dictionary.")
            return payload

    def _iter_coordinate_pairs(coordinates: Any):
        if (
            isinstance(coordinates, list | tuple)
            and len(coordinates) >= 2
            and isinstance(coordinates[0], int | float)
            and isinstance(coordinates[1], int | float)
        ):
            yield float(coordinates[0]), float(coordinates[1])
            return

        if isinstance(coordinates, Iterable) and not isinstance(coordinates, str | bytes):
            for item in coordinates:
                yield from _iter_coordinate_pairs(item)

    def iter_geojson_lon_lat(geojson: dict[str, Any]):
        for feature in geojson.get("features", []):
            geometry = feature.get("geometry") or {}
            yield from _iter_coordinate_pairs(geometry.get("coordinates", []))

    def geojson_center(geojson: dict[str, Any]) -> tuple[float, float]:
        pairs = list(iter_geojson_lon_lat(geojson))
        if not pairs:
            return 20.5937, 78.9629
        longitudes = [pair[0] for pair in pairs]
        latitudes = [pair[1] for pair in pairs]
        return (min(latitudes) + max(latitudes)) / 2, (min(longitudes) + max(longitudes)) / 2

    def property_values(geojson: dict[str, Any], key: str) -> list[str]:
        values = []
        for feature in geojson.get("features", []):
            value = feature.get("properties", {}).get(key)
            if value is not None:
                values.append(str(value))
        return values

    def subset_geojson_by_uid(geojson: dict[str, Any], uid: str) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [
                feature
                for feature in geojson.get("features", [])
                if str(feature.get("properties", {}).get("uid")) == str(uid)
            ],
        }

    def describe_api_exception(exc: Exception) -> str:
        detail = str(exc).strip() or repr(exc)
        cors_clues = (
            "Could not reach",
            "Failed to fetch",
            "NetworkError",
            "Load failed",
            "TypeError",
        )
        if any(clue in detail for clue in cors_clues):
            return (
                f"{detail}\n\n"
                "If this happens on GitHub Pages after entering a valid key, the likely cause "
                "is browser CORS. The CoRE Stack API must allow the deployed origin "
                "`https://amit-spatial.github.io` and the `X-API-Key` request header."
            )
        return detail

    def layer_group_counts(
        layers: list[dict[str, Any]],
        groups: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        rows = []
        for group_name, keywords in groups.items():
            count = 0
            for layer in layers:
                text = " ".join(
                    str(layer.get(key, ""))
                    for key in ("dataset_name", "layer_name", "layer_type", "gee_asset_path")
                ).lower()
                if any(keyword in text for keyword in keywords):
                    count += 1
            rows.append({"evidence_group": group_name, "layer_count": count})
        return rows

    def matching_layers(
        layers: list[dict[str, Any]],
        keywords: list[str],
    ) -> list[dict[str, Any]]:
        records = []
        for layer in layers:
            text = " ".join(
                str(layer.get(key, ""))
                for key in ("dataset_name", "layer_name", "layer_type", "gee_asset_path")
            ).lower()
            if any(keyword in text for keyword in keywords):
                records.append(layer)
        return records

    def indicator_rows(record: dict[str, Any], columns: list[str]) -> list[dict[str, Any]]:
        rows = []
        for column in columns:
            value = record.get(column)
            if isinstance(value, list):
                display_value = f"{len(value)} item(s)"
            else:
                display_value = value
            rows.append({"indicator": column, "value": display_value})
        return rows

    def narrative_summary(record: dict[str, Any], uid: str) -> str:
        villages = record.get("mws_intersect_villages") or []
        swb = record.get("mws_intersect_swb") or []
        return (
            f"MWS `{uid}` intersects {len(villages)} village record(s), "
            f"has {record.get('total_nrega_assets', 0)} NREGA assets in the KYL snapshot, "
            f"and references {len(swb)} surface-water-body point(s). "
            f"Average precipitation is {record.get('avg_precipitation', 'NA')}, "
            f"average runoff is {record.get('avg_runoff', 'NA')}, and the cropping "
            f"intensity average is {record.get('cropping_intensity_avg', 'NA')}."
        )

    try:
        repo_root = Path(__file__).resolve().parents[1]
    except NameError:
        repo_root = Path.cwd()

    return (
        CoreStackPublicAPIError,
        CoreStackPublicClient,
        CoreStackSettings,
        EVIDENCE_GROUPS,
        INDICATOR_SETS,
        TOUR_STEPS,
        alt,
        describe_api_exception,
        folium,
        geojson_center,
        indicator_rows,
        layer_group_counts,
        matching_layers,
        mo,
        narrative_summary,
        pl,
        property_values,
        repo_root,
        subset_geojson_by_uid,
    )


@app.cell
def _(CoreStackSettings, repo_root):
    settings = CoreStackSettings.from_env(repo_root / ".env")
    return (settings,)


@app.cell
def _(mo):
    mo.vstack(
        [
            mo.md(r"""
            # Guided CoRE Stack Map Tour

            A map is not useful just because it has layers. This app teaches a user
            how to move from boundary, to evidence, to interpretation, to a small
            self-arranged dashboard.
            """),
            mo.callout(
                """
                Use this as a facilitation applet: select a landscape, pick a
                micro-watershed, follow the tour prompts, and assemble only the panels
                needed for the next planning conversation.

                Need a key? Open the [CoRE Stack dashboard](https://dashboard.core-stack.org/).
                """,
                kind="info",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## What This Tour Practices

    - orienting to villages and micro-watersheds before reading indicators
    - using tooltips to ask "where am I and what is this?"
    - comparing maps with time-series signals
    - checking which evidence layers exist for a place
    - building a compact dashboard for field or team discussion

    ```python
    selected_mws = "3_8320"
    profile = client.mws_kyl_indicators(..., mws_id=selected_mws)[0]
    time_series = client.mws_data(..., mws_id=selected_mws)["time_series"]
    ```
    """)
    return


@app.cell
def _(mo, settings):
    base_url_input = mo.ui.text(
        value=settings.public_api_base_url,
        label="Public API base URL",
        full_width=True,
    )
    api_key_override = mo.ui.text(
        value="",
        kind="password",
        label="CoRE Stack API key",
        placeholder="Paste an API key here; local runs can also use .env",
        full_width=True,
    )
    mo.vstack([base_url_input, api_key_override])
    return api_key_override, base_url_input


@app.cell
def _(CoreStackPublicClient, api_key_override, base_url_input, settings):
    api_key = api_key_override.value.strip() or settings.public_api_key
    client = (
        CoreStackPublicClient(
            api_key=api_key,
            base_url=base_url_input.value.strip(),
        )
        if api_key
        else None
    )
    return (client,)


@app.cell
def _(CoreStackPublicAPIError, client, describe_api_exception, mo):
    mo.stop(
        client is None,
        mo.callout(
            "Paste a CoRE Stack API key above to activate the guided map tour.",
            kind="neutral",
        ),
    )
    try:
        active_locations = client.active_locations()
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not load active locations.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    state_names = [state["label"] for state in active_locations]
    return active_locations, state_names


@app.cell
def _(mo, state_names):
    mo.stop(
        not state_names,
        mo.callout("No active locations were returned by the API.", kind="warn"),
    )
    state_selector = mo.ui.dropdown(
        options=state_names,
        value=state_names[0],
        label="State",
        full_width=True,
    )
    state_selector
    return (state_selector,)


@app.cell
def _(active_locations, state_selector):
    selected_state_record = next(
        state for state in active_locations if state["label"] == state_selector.value
    )
    district_names = [district["label"] for district in selected_state_record["district"]]
    return district_names, selected_state_record


@app.cell
def _(district_names, mo):
    district_selector = mo.ui.dropdown(
        options=district_names,
        value=district_names[0],
        label="District",
        full_width=True,
    )
    district_selector
    return (district_selector,)


@app.cell
def _(district_selector, selected_state_record):
    selected_district_record = next(
        district
        for district in selected_state_record["district"]
        if district["label"] == district_selector.value
    )
    tehsil_names = [block["label"] for block in selected_district_record["blocks"]]
    return (tehsil_names,)


@app.cell
def _(mo, tehsil_names):
    tehsil_selector = mo.ui.dropdown(
        options=tehsil_names,
        value=tehsil_names[0],
        label="Tehsil / block",
        full_width=True,
    )
    load_location = mo.ui.run_button(label="Load tour")
    mo.hstack([tehsil_selector, load_location], widths=[4, 1])
    return load_location, tehsil_selector


@app.cell
def _(load_location, mo):
    is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not is_script_mode and not load_location.value,
        mo.md("Choose a location, then load the guided tour."),
    )
    return


@app.cell
def _(
    CoreStackPublicAPIError,
    client,
    describe_api_exception,
    district_selector,
    mo,
    state_selector,
    tehsil_selector,
):
    selected_scope = {
        "state": state_selector.value,
        "district": district_selector.value,
        "tehsil": tehsil_selector.value,
    }
    try:
        generated_layers = client.generated_layer_urls(**selected_scope)
        mws_geojson = client.mws_geometries(**selected_scope)
        village_geojson = client.village_geometries(**selected_scope)
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not load tour geography.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return generated_layers, mws_geojson, selected_scope, village_geojson


@app.cell
def _(EVIDENCE_GROUPS, TOUR_STEPS, mo, mws_geojson, property_values):
    mws_uids = property_values(mws_geojson, "uid")
    mo.stop(
        not mws_uids,
        mo.callout("No MWS features were returned for this location.", kind="warn"),
    )
    tour_step = mo.ui.dropdown(
        options=list(TOUR_STEPS.keys()),
        value="1. Orient to the landscape",
        label="Tour step",
        full_width=True,
    )
    mws_selector = mo.ui.dropdown(
        options=mws_uids,
        value=mws_uids[0],
        label="Micro-watershed uid",
        full_width=True,
    )
    evidence_group = mo.ui.dropdown(
        options=list(EVIDENCE_GROUPS.keys()),
        value="Water, runoff, and drought",
        label="Evidence group",
        full_width=True,
    )
    mo.vstack([tour_step, mo.hstack([mws_selector, evidence_group])])
    return evidence_group, mws_selector, mws_uids, tour_step


@app.cell
def _(TOUR_STEPS, mo, tour_step):
    step = TOUR_STEPS[tour_step.value]
    mo.callout(step["prompt"], kind=step["kind"])
    return


@app.cell
def _(
    CoreStackPublicAPIError,
    client,
    describe_api_exception,
    mo,
    mws_selector,
    selected_scope,
):
    selected_mws_id = mws_selector.value
    try:
        mws_timeseries_payload = client.mws_data(**selected_scope, mws_id=selected_mws_id)
        mws_kyl_payload = client.mws_kyl_indicators(**selected_scope, mws_id=selected_mws_id)
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not load MWS profile for `{selected_mws_id}`.\n\n"
                f"{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return mws_kyl_payload, mws_timeseries_payload, selected_mws_id


@app.cell
def _(mws_kyl_payload, mws_timeseries_payload, narrative_summary, pl, selected_mws_id):
    mws_timeseries_df = pl.DataFrame(mws_timeseries_payload.get("time_series", []))
    kyl_record = mws_kyl_payload[0] if mws_kyl_payload else {}
    narrative = narrative_summary(kyl_record, selected_mws_id)
    return kyl_record, mws_timeseries_df, narrative


@app.cell
def _(
    EVIDENCE_GROUPS,
    evidence_group,
    generated_layers,
    layer_group_counts,
    matching_layers,
    pl,
):
    evidence_counts_df = pl.DataFrame(layer_group_counts(generated_layers, EVIDENCE_GROUPS))
    selected_group_layers = matching_layers(
        generated_layers,
        EVIDENCE_GROUPS[evidence_group.value],
    )
    selected_group_layers_df = (
        pl.DataFrame(selected_group_layers)
        if selected_group_layers
        else pl.DataFrame(
            {
                "dataset_name": [],
                "layer_name": [],
                "layer_type": [],
                "layer_url": [],
                "gee_asset_path": [],
            }
        )
    )
    return evidence_counts_df, selected_group_layers, selected_group_layers_df


@app.cell
def _(INDICATOR_SETS, mo):
    chart_group = mo.ui.dropdown(
        options=["Water balance", "Vegetation"],
        value="Water balance",
        label="Chart family",
        full_width=True,
    )
    indicator_set = mo.ui.dropdown(
        options=list(INDICATOR_SETS.keys()),
        value="Water stress",
        label="Indicator set",
        full_width=True,
    )
    show_map = mo.ui.checkbox(value=True, label="Map")
    show_time_series = mo.ui.checkbox(value=True, label="Time series")
    show_layers = mo.ui.checkbox(value=True, label="Evidence layers")
    show_indicators = mo.ui.checkbox(value=True, label="Indicators")
    show_brief = mo.ui.checkbox(value=True, label="Brief")
    mo.vstack(
        [
            mo.md("## Assemble Your Dashboard"),
            mo.hstack([chart_group, indicator_set]),
            mo.hstack([show_map, show_time_series, show_layers, show_indicators, show_brief]),
        ]
    )
    return (
        chart_group,
        indicator_set,
        show_brief,
        show_indicators,
        show_layers,
        show_map,
        show_time_series,
    )


@app.cell
def _(
    folium,
    geojson_center,
    kyl_record,
    mo,
    mws_geojson,
    selected_mws_id,
    selected_scope,
    subset_geojson_by_uid,
    tour_step,
    village_geojson,
):
    map_center = geojson_center(mws_geojson)
    tour_map = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")

    folium.GeoJson(
        village_geojson,
        name="Villages",
        style_function=lambda _: {"color": "#64748b", "weight": 1, "fillOpacity": 0.04},
    ).add_to(tour_map)

    folium.GeoJson(
        mws_geojson,
        name="All MWS",
        tooltip=folium.GeoJsonTooltip(fields=["uid"], aliases=["MWS uid"]),
        style_function=lambda _: {"color": "#94a3b8", "weight": 1, "fillOpacity": 0.02},
    ).add_to(tour_map)

    selected_geojson = subset_geojson_by_uid(mws_geojson, selected_mws_id)
    folium.GeoJson(
        selected_geojson,
        name="Selected MWS",
        tooltip=folium.GeoJsonTooltip(fields=["uid"], aliases=["Selected MWS"]),
        style_function=lambda _: {
            "color": "#dc2626",
            "weight": 4,
            "fillColor": "#f97316",
            "fillOpacity": 0.22,
        },
    ).add_to(tour_map)

    if tour_step.value in {
        "3. Read water and vegetation signals",
        "4. Ask what action this suggests",
        "5. Assemble your dashboard",
    }:
        for swb in kyl_record.get("mws_intersect_swb", [])[:80]:
            lat = swb.get("latitude")
            lon = swb.get("longitude")
            if lat is None or lon is None:
                continue
            label = swb.get("swbName") or swb.get("swbId") or "surface water body"
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="#0284c7",
                fill=True,
                fill_opacity=0.7,
                tooltip=f"Surface water body: {label}",
            ).add_to(tour_map)

    folium.LayerControl(collapsed=False).add_to(tour_map)
    title = f"{selected_scope['tehsil']}, {selected_scope['district']}, {selected_scope['state']}"
    tour_map_panel = mo.vstack(
        [
            mo.md(f"### Guided Map: {title}"),
            mo.Html(tour_map._repr_html_()),
        ]
    )
    return (tour_map_panel,)


@app.cell
def _(alt, chart_group, mo, mws_timeseries_df, selected_mws_id):
    columns = (
        ["precipitation", "runoff", "et"]
        if chart_group.value == "Water balance"
        else ["ndvi_crop", "ndvi_shrub", "ndvi_tree"]
    )
    available_columns = [column for column in columns if column in mws_timeseries_df.columns]
    chart_title = f"{chart_group.value}: `{selected_mws_id}`"
    long_df = mws_timeseries_df.unpivot(
        index="date",
        on=available_columns,
        variable_name="metric",
        value_name="value",
    )
    time_series_chart = (
        alt.Chart(long_df)
        .mark_line(point=False)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=["date:T", "metric:N", "value:Q"],
        )
        .properties(height=330, title=chart_title)
        .interactive()
    )
    time_series_panel = mo.vstack(
        [
            mo.md("### Time-Series Signals"),
            mo.callout(
                "Look for timing and mismatch: rainfall without vegetation response, "
                "runoff spikes, or low dry-season NDVI can each suggest different questions.",
                kind="neutral",
            ),
            time_series_chart,
        ]
    )
    return (time_series_panel,)


@app.cell
def _(alt, evidence_counts_df, mo, selected_group_layers_df):
    evidence_chart = (
        alt.Chart(evidence_counts_df)
        .mark_bar()
        .encode(
            y=alt.Y("evidence_group:N", title="Evidence group", sort="-x"),
            x=alt.X("layer_count:Q", title="Layer count"),
            tooltip=["evidence_group", "layer_count"],
        )
        .properties(height=260)
    )
    layers_panel = mo.vstack(
        [
            mo.md("### Evidence Layer Availability"),
            evidence_chart,
            mo.ui.dataframe(
                selected_group_layers_df.select(
                    [
                        column
                        for column in [
                            "dataset_name",
                            "layer_name",
                            "layer_type",
                            "layer_url",
                            "gee_asset_path",
                        ]
                        if column in selected_group_layers_df.columns
                    ]
                )
            ),
        ]
    )
    return (layers_panel,)


@app.cell
def _(INDICATOR_SETS, indicator_rows, indicator_set, kyl_record, mo, pl):
    rows = indicator_rows(kyl_record, INDICATOR_SETS[indicator_set.value])
    indicators_panel = mo.vstack(
        [
            mo.md(f"### Indicator Reading: {indicator_set.value}"),
            mo.ui.dataframe(pl.DataFrame(rows)),
        ]
    )
    return (indicators_panel,)


@app.cell
def _(mo, narrative, selected_mws_id, selected_scope):
    brief_panel = mo.vstack(
        [
            mo.md(f"### Interpretation Brief: `{selected_mws_id}`"),
            mo.callout(narrative, kind="success"),
            mo.md(
                f"""
                Suggested next conversation for {selected_scope["tehsil"]}:

                - Which village users recognize this MWS and its water bodies?
                - Which layer should be checked first: water, vegetation, restoration,
                  or social context?
                - What field evidence would confirm or challenge the remote-sensing signal?
                - Which output should be copied into a planning note or meeting agenda?
                """
            ),
        ]
    )
    return (brief_panel,)


@app.cell
def _(
    brief_panel,
    indicators_panel,
    layers_panel,
    mo,
    show_brief,
    show_indicators,
    show_layers,
    show_map,
    show_time_series,
    time_series_panel,
    tour_map_panel,
):
    panels = []
    if show_map.value:
        panels.append(tour_map_panel)
    if show_time_series.value:
        panels.append(time_series_panel)
    if show_layers.value:
        panels.append(layers_panel)
    if show_indicators.value:
        panels.append(indicators_panel)
    if show_brief.value:
        panels.append(brief_panel)

    mo.vstack(panels)
    return


@app.cell
def _(CoreStackPublicAPIError, client, mo, selected_mws_id, selected_scope):
    try:
        report_payload = client.mws_report(**selected_scope, mws_id=selected_mws_id)
        report_url = report_payload.get("Mws_report_url")
        report_output = (
            mo.md(f"## Existing MWS Report\n\n[Open generated MWS report]({report_url})")
            if report_url
            else mo.md("## Existing MWS Report\n\nNo report URL returned for this MWS.")
        )
    except CoreStackPublicAPIError as exc:
        report_output = mo.callout(
            f"Report URL is not available for this MWS yet. API response: {exc}",
            kind="warn",
        )
    report_output
    return


if __name__ == "__main__":
    app.run()
