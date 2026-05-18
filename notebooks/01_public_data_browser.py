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

    def feature_count(geojson: dict[str, Any]) -> int:
        return len(geojson.get("features", []))

    def property_values(geojson: dict[str, Any], key: str) -> list[str]:
        values = []
        for feature in geojson.get("features", []):
            value = feature.get("properties", {}).get(key)
            if value is not None:
                values.append(str(value))
        return values

    try:
        repo_root = Path(__file__).resolve().parents[1]
    except NameError:
        repo_root = Path.cwd()

    return (
        CoreStackPublicAPIError,
        CoreStackPublicClient,
        CoreStackSettings,
        alt,
        feature_count,
        folium,
        geojson_center,
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
    mo.md(r"""
    # CoRE Stack Public Data Browser

    Explore active CoRE Stack geographies, inspect published layers, and drill into
    micro-watershed analytics using the current public API surface.
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
def _(CoreStackPublicClient, api_key_override, base_url_input, mo, settings):
    api_key = api_key_override.value.strip() or settings.public_api_key
    mo.stop(
        not api_key,
        mo.md("Paste a CoRE Stack API key above to start. Local runs can also use `.env`."),
    )
    client = CoreStackPublicClient(
        api_key=api_key,
        base_url=base_url_input.value.strip(),
    )
    return (client,)


@app.cell
def _(client):
    active_locations = client.active_locations()
    state_names = [state["label"] for state in active_locations]
    return active_locations, state_names


@app.cell
def _(mo, state_names):
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
    load_location = mo.ui.run_button(label="Load selected location")
    mo.hstack([tehsil_selector, load_location], widths=[4, 1])
    return load_location, tehsil_selector


@app.cell
def _(load_location, mo):
    is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not is_script_mode and not load_location.value,
        mo.md("Choose a location, then load it."),
    )
    return


@app.cell
def _(client, district_selector, state_selector, tehsil_selector):
    selected_scope = {
        "state": state_selector.value,
        "district": district_selector.value,
        "tehsil": tehsil_selector.value,
    }
    generated_layers = client.generated_layer_urls(**selected_scope)
    mws_geojson = client.mws_geometries(**selected_scope)
    village_geojson = client.village_geometries(**selected_scope)
    return generated_layers, mws_geojson, selected_scope, village_geojson


@app.cell
def _(
    feature_count,
    generated_layers,
    mo,
    mws_geojson,
    selected_scope,
    village_geojson,
):
    metrics = mo.hstack(
        [
            mo.stat(label="Active scope", value=selected_scope["tehsil"]),
            mo.stat(label="Published layers", value=len(generated_layers)),
            mo.stat(label="MWS geometries", value=feature_count(mws_geojson)),
            mo.stat(label="Village geometries", value=feature_count(village_geojson)),
        ]
    )
    metrics
    return


@app.cell
def _(generated_layers, pl):
    layers_df = pl.DataFrame(generated_layers)
    layer_type_counts = layers_df.group_by("layer_type").len().sort("len", descending=True)
    dataset_counts = layers_df.group_by("dataset_name").len().sort("len", descending=True)
    return dataset_counts, layer_type_counts, layers_df


@app.cell
def _(alt, dataset_counts, layer_type_counts, mo):
    type_chart = (
        alt.Chart(layer_type_counts)
        .mark_bar()
        .encode(
            x=alt.X("layer_type:N", title="Layer type"),
            y=alt.Y("len:Q", title="Count"),
            color=alt.Color("layer_type:N", legend=None),
            tooltip=["layer_type", "len"],
        )
        .properties(height=220)
    )
    dataset_chart = (
        alt.Chart(dataset_counts.head(18))
        .mark_bar()
        .encode(
            y=alt.Y("dataset_name:N", title="Dataset", sort="-x"),
            x=alt.X("len:Q", title="Count"),
            tooltip=["dataset_name", "len"],
        )
        .properties(height=420)
    )
    mo.hstack([type_chart, dataset_chart], widths=[1, 2])
    return


@app.cell
def _(layers_df, mo):
    mo.ui.dataframe(layers_df)
    return


@app.cell
def _(
    folium,
    geojson_center,
    mo,
    mws_geojson,
    selected_scope,
    village_geojson,
):
    map_center = geojson_center(mws_geojson)
    location_map = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")
    folium.GeoJson(
        village_geojson,
        name="Villages",
        style_function=lambda _: {"color": "#64748b", "weight": 1, "fillOpacity": 0.05},
    ).add_to(location_map)
    folium.GeoJson(
        mws_geojson,
        name="Micro-watersheds",
        tooltip=folium.GeoJsonTooltip(fields=["uid"], aliases=["MWS uid"]),
        style_function=lambda _: {"color": "#2563eb", "weight": 2, "fillOpacity": 0.08},
    ).add_to(location_map)
    folium.LayerControl(collapsed=False).add_to(location_map)
    map_title = (
        f"{selected_scope['tehsil']}, {selected_scope['district']}, {selected_scope['state']}"
    )
    mo.vstack([mo.md(f"## Geometry Preview: {map_title}"), mo.Html(location_map._repr_html_())])
    return


@app.cell
def _(mo, mws_geojson, property_values):
    mws_uids = property_values(mws_geojson, "uid")
    mws_selector = mo.ui.dropdown(
        options=mws_uids,
        value=mws_uids[0],
        label="Micro-watershed uid",
        full_width=True,
    )
    mws_selector
    return (mws_selector,)


@app.cell
def _(client, mws_selector, selected_scope):
    selected_mws_id = mws_selector.value
    mws_timeseries_payload = client.mws_data(**selected_scope, mws_id=selected_mws_id)
    mws_kyl_payload = client.mws_kyl_indicators(**selected_scope, mws_id=selected_mws_id)
    return mws_kyl_payload, mws_timeseries_payload, selected_mws_id


@app.cell
def _(mws_timeseries_payload, pl):
    mws_timeseries_df = pl.DataFrame(mws_timeseries_payload.get("time_series", []))
    return (mws_timeseries_df,)


@app.cell
def _(alt, mo, mws_timeseries_df, selected_mws_id):
    value_columns = [
        column
        for column in ["precipitation", "runoff", "et", "ndvi_crop", "ndvi_shrub", "ndvi_tree"]
        if column in mws_timeseries_df.columns
    ]
    timeseries_long = mws_timeseries_df.unpivot(
        index="date",
        on=value_columns,
        variable_name="metric",
        value_name="value",
    )
    timeseries_chart = (
        alt.Chart(timeseries_long)
        .mark_line(point=False)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("value:Q", title="Value"),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=["date:T", "metric:N", "value:Q"],
        )
        .properties(height=360)
        .interactive()
    )
    mo.vstack([mo.md(f"## MWS Time Series: `{selected_mws_id}`"), timeseries_chart])
    return


@app.cell
def _(mo, mws_kyl_payload, mws_timeseries_df, pl):
    kyl_df = pl.DataFrame(mws_kyl_payload) if mws_kyl_payload else pl.DataFrame()
    mo.vstack(
        [
            mo.md("## MWS Indicator Snapshot"),
            mo.ui.dataframe(kyl_df),
            mo.md("## Raw Time Series"),
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
            mo.md(f"[Open generated MWS report]({report_url})")
            if report_url
            else mo.md("No report URL returned for this MWS.")
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
