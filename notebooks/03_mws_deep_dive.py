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
            headers = {
                "Accept": "application/json",
                "X-API-Key": self.api_key,
            }

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

    def metric_total(frame: pl.DataFrame, column: str) -> float | None:
        if column not in frame.columns or frame.is_empty():
            return None
        return frame.select(pl.col(column).cast(pl.Float64).sum()).item()

    def metric_mean(frame: pl.DataFrame, column: str) -> float | None:
        if column not in frame.columns or frame.is_empty():
            return None
        return frame.select(pl.col(column).cast(pl.Float64).mean()).item()

    def fmt(value: float | int | None, digits: int = 2) -> str:
        if value is None:
            return "not available"
        return f"{value:,.{digits}f}"

    def indicator_table(record: dict[str, Any], columns: list[str]) -> pl.DataFrame:
        rows = [{"indicator": column, "value": record.get(column)} for column in columns]
        return pl.DataFrame(rows)

    try:
        repo_root = Path(__file__).resolve().parents[1]
    except NameError:
        repo_root = Path.cwd()

    return (
        CoreStackPublicAPIError,
        CoreStackPublicClient,
        CoreStackSettings,
        alt,
        describe_api_exception,
        fmt,
        folium,
        geojson_center,
        indicator_table,
        metric_mean,
        metric_total,
        mo,
        pl,
        property_values,
        repo_root,
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
            # CoRE Stack MWS Deep Dive

            Select one micro-watershed and turn its time series, KYL indicators,
            village context, and report link into a compact analytical brief.
            """),
            mo.callout(
                """
                This notebook is designed for researchers, field teams, and planners who need
                both interpretation and reusable code logic. It stays readable before a key is
                entered, then becomes fully reactive once the live API is available.

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
    ## Analytical Frame

    A useful MWS brief usually needs four layers of reasoning:

    - Hydrology: precipitation, runoff, ET, and runoff coefficient
    - Vegetation: crop, shrub, and tree NDVI signals through time
    - Place context: MWS boundary, nearby villages, terrain and land-cover indicators
    - Actionability: restoration classes, water stress, trend signals, and report links

    ```python
    timeseries = client.mws_data(..., mws_id=uid)["time_series"]
    indicators = client.mws_kyl_indicators(..., mws_id=uid)[0]
    runoff_coefficient = sum(row["runoff"] for row in timeseries) / sum(
        row["precipitation"] for row in timeseries
    )
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
            "Paste a CoRE Stack API key above to activate the live MWS deep dive.",
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
    load_location = mo.ui.run_button(label="Load MWS list")
    mo.hstack([tehsil_selector, load_location], widths=[4, 1])
    return load_location, tehsil_selector


@app.cell
def _(load_location, mo):
    is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not is_script_mode and not load_location.value,
        mo.md("Choose a location, then load the MWS list."),
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
        mws_geojson = client.mws_geometries(**selected_scope)
        village_geojson = client.village_geometries(**selected_scope)
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not load MWS geometries.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return mws_geojson, selected_scope, village_geojson


@app.cell
def _(mo, mws_geojson, property_values):
    mws_uids = property_values(mws_geojson, "uid")
    mo.stop(
        not mws_uids,
        mo.callout("No MWS features were returned for this location.", kind="warn"),
    )
    mws_selector = mo.ui.dropdown(
        options=mws_uids,
        value=mws_uids[0],
        label="Micro-watershed uid",
        full_width=True,
    )
    mws_selector
    return mws_selector, mws_uids


@app.cell
def _(CoreStackPublicAPIError, client, describe_api_exception, mo, mws_selector, selected_scope):
    selected_mws_id = mws_selector.value
    try:
        mws_timeseries_payload = client.mws_data(**selected_scope, mws_id=selected_mws_id)
        mws_kyl_payload = client.mws_kyl_indicators(**selected_scope, mws_id=selected_mws_id)
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not load MWS analytics for `{selected_mws_id}`.\n\n"
                f"{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return mws_kyl_payload, mws_timeseries_payload, selected_mws_id


@app.cell
def _(mws_kyl_payload, mws_timeseries_payload, pl):
    mws_timeseries_df = pl.DataFrame(mws_timeseries_payload.get("time_series", []))
    kyl_record = mws_kyl_payload[0] if mws_kyl_payload else {}
    kyl_df = pl.DataFrame(mws_kyl_payload) if mws_kyl_payload else pl.DataFrame()
    return kyl_df, kyl_record, mws_timeseries_df


@app.cell
def _(fmt, metric_mean, metric_total, mo, mws_timeseries_df, selected_mws_id):
    precipitation_total = metric_total(mws_timeseries_df, "precipitation")
    runoff_total = metric_total(mws_timeseries_df, "runoff")
    et_total = metric_total(mws_timeseries_df, "et")
    ndvi_tree_mean = metric_mean(mws_timeseries_df, "ndvi_tree")
    runoff_coefficient = (
        runoff_total / precipitation_total
        if precipitation_total not in (None, 0) and runoff_total is not None
        else None
    )
    mo.hstack(
        [
            mo.stat(label="MWS uid", value=selected_mws_id),
            mo.stat(label="Precipitation total", value=fmt(precipitation_total)),
            mo.stat(label="Runoff total", value=fmt(runoff_total)),
            mo.stat(label="ET total", value=fmt(et_total)),
            mo.stat(label="Runoff coefficient", value=fmt(runoff_coefficient, 3)),
            mo.stat(label="Mean tree NDVI", value=fmt(ndvi_tree_mean, 3)),
        ]
    )
    return


@app.cell
def _(alt, mo, mws_timeseries_df, selected_mws_id):
    water_columns = [
        column
        for column in ["precipitation", "runoff", "et"]
        if column in mws_timeseries_df.columns
    ]
    water_long = mws_timeseries_df.unpivot(
        index="date",
        on=water_columns,
        variable_name="metric",
        value_name="value",
    )
    water_chart = (
        alt.Chart(water_long)
        .mark_line(point=False)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=["date:T", "metric:N", "value:Q"],
        )
        .properties(height=340)
        .interactive()
    )
    mo.vstack([mo.md(f"## Water Balance Signals: `{selected_mws_id}`"), water_chart])
    return


@app.cell
def _(alt, mo, mws_timeseries_df):
    ndvi_columns = [
        column
        for column in ["ndvi_crop", "ndvi_shrub", "ndvi_tree"]
        if column in mws_timeseries_df.columns
    ]
    ndvi_long = mws_timeseries_df.unpivot(
        index="date",
        on=ndvi_columns,
        variable_name="metric",
        value_name="value",
    )
    ndvi_chart = (
        alt.Chart(ndvi_long)
        .mark_line(point=False)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("value:Q", title="NDVI"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=["date:T", "metric:N", "value:Q"],
        )
        .properties(height=340)
        .interactive()
    )
    mo.vstack([mo.md("## Vegetation Signals"), ndvi_chart])
    return


@app.cell
def _(indicator_table, kyl_record, mo):
    indicator_groups = {
        "Water stress and hydrology": [
            "avg_precipitation",
            "avg_runoff",
            "avg_number_dry_spell",
            "avg_wsr_ratio_kharif",
            "avg_wsr_ratio_rabi",
            "avg_wsr_ratio_zaid",
        ],
        "Cropping and surface water": [
            "cropping_intensity_avg",
            "cropping_intensity_trend",
            "avg_single_cropped",
            "avg_double_cropped",
            "avg_triple_cropped",
            "avg_kharif_surface_water_mws",
            "avg_rabi_surface_water_mws",
            "avg_zaid_surface_water_mws",
        ],
        "Restoration and land cover": [
            "area_protection",
            "area_wide_scale_restoration",
            "area_tree_on_slope",
            "area_shrubs_on_slope",
            "area_crops_on_plain",
            "lulc_forest_area",
            "lulc_shrub_area",
            "lulc_crop_area",
        ],
        "Governance and pressure signals": [
            "drought_category",
            "aquifer_class",
            "terraincluster_id",
            "mining",
            "factory_csr",
            "green_credit",
            "lcw_conflict",
            "urbanization_area",
        ],
    }
    group_selector = mo.ui.dropdown(
        options=list(indicator_groups.keys()),
        value="Water stress and hydrology",
        label="Indicator family",
        full_width=True,
    )
    indicator_subset = indicator_table(kyl_record, indicator_groups[group_selector.value])
    mo.vstack(
        [
            group_selector,
            mo.ui.dataframe(indicator_subset),
        ]
    )
    return


@app.cell
def _(folium, geojson_center, mo, mws_geojson, selected_mws_id, selected_scope, village_geojson):
    map_center = geojson_center(mws_geojson)
    mws_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")
    folium.GeoJson(
        village_geojson,
        name="Villages",
        style_function=lambda _: {"color": "#64748b", "weight": 1, "fillOpacity": 0.04},
    ).add_to(mws_map)

    def mws_style(feature):
        uid = str(feature.get("properties", {}).get("uid"))
        if uid == str(selected_mws_id):
            return {"color": "#dc2626", "weight": 4, "fillOpacity": 0.18}
        return {"color": "#2563eb", "weight": 1.5, "fillOpacity": 0.04}

    folium.GeoJson(
        mws_geojson,
        name="Micro-watersheds",
        tooltip=folium.GeoJsonTooltip(fields=["uid"], aliases=["MWS uid"]),
        style_function=mws_style,
    ).add_to(mws_map)
    folium.LayerControl(collapsed=False).add_to(mws_map)
    title = f"{selected_scope['tehsil']}, {selected_scope['district']}, {selected_scope['state']}"
    mo.vstack([mo.md(f"## Place Context: {title}"), mo.Html(mws_map._repr_html_())])
    return


@app.cell
def _(kyl_df, mo, mws_timeseries_df):
    mo.vstack(
        [
            mo.md("## Raw Tables"),
            mo.md("### KYL Indicator Row"),
            mo.ui.dataframe(kyl_df),
            mo.md("### MWS Time Series"),
            mo.ui.dataframe(mws_timeseries_df),
        ]
    )
    return


@app.cell
def _(CoreStackPublicAPIError, client, mo, selected_mws_id, selected_scope):
    try:
        report_payload = client.mws_report(**selected_scope, mws_id=selected_mws_id)
        report_url = report_payload.get("Mws_report_url")
        report_output = (
            mo.md(f"## Report Link\n\n[Open generated MWS report]({report_url})")
            if report_url
            else mo.md("## Report Link\n\nNo report URL returned for this MWS.")
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
