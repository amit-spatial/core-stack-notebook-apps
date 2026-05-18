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
    import json
    import os
    from collections.abc import Iterable
    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any
    from urllib.parse import urlparse

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
    LAYER_COLUMNS = (
        "dataset_name",
        "layer_name",
        "layer_type",
        "layer_version",
        "layer_url",
        "gee_asset_path",
        "style_url",
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

    def layer_records_to_frame(records: list[dict[str, Any]]) -> pl.DataFrame:
        if records:
            frame = pl.DataFrame(records)
        else:
            frame = pl.DataFrame({column: [] for column in LAYER_COLUMNS})

        for column in LAYER_COLUMNS:
            if column not in frame.columns:
                frame = frame.with_columns(pl.lit("").alias(column))

        return frame.with_columns(
            [pl.col(column).cast(pl.Utf8).fill_null("") for column in LAYER_COLUMNS]
        ).select(list(LAYER_COLUMNS))

    def layer_host(layer_url: str) -> str:
        parsed = urlparse(layer_url)
        return parsed.netloc or "asset path"

    def filter_layer_records(
        records: list[dict[str, Any]],
        *,
        layer_type: str,
        dataset: str,
        term: str,
    ) -> list[dict[str, Any]]:
        normalized_term = term.strip().lower()
        filtered = []
        for record in records:
            if layer_type != "All" and record.get("layer_type") != layer_type:
                continue
            if dataset != "All" and record.get("dataset_name") != dataset:
                continue
            haystack = " ".join(str(record.get(column, "")) for column in LAYER_COLUMNS).lower()
            if normalized_term and normalized_term not in haystack:
                continue
            filtered.append(record)
        return filtered

    def layer_label(record: dict[str, Any], index: int) -> str:
        dataset = record.get("dataset_name") or "Dataset"
        name = record.get("layer_name") or f"Layer {index + 1}"
        layer_type = record.get("layer_type") or "layer"
        return f"{dataset} | {name} ({layer_type})"

    def layer_manifest(records: list[dict[str, Any]]) -> str:
        payload = [
            {
                "dataset_name": record.get("dataset_name", ""),
                "layer_name": record.get("layer_name", ""),
                "layer_type": record.get("layer_type", ""),
                "layer_url": record.get("layer_url", ""),
                "gee_asset_path": record.get("gee_asset_path", ""),
                "style_url": record.get("style_url", ""),
            }
            for record in records[:25]
        ]
        return json.dumps(payload, indent=2)

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
        feature_count,
        filter_layer_records,
        folium,
        geojson_center,
        layer_host,
        layer_label,
        layer_manifest,
        layer_records_to_frame,
        mo,
        pl,
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
            # CoRE Stack Exploratory Layer Studio

            Build a quick mental model of a place by browsing its generated layers,
            filtering the catalog, inspecting layer URLs, and previewing the MWS/village frame.
            """),
            mo.callout(
                """
                This app is useful before a deep analysis begins. It answers:
                which datasets exist here, which are vector or raster, which URLs can be reused,
                and what geography each layer belongs to.

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
    ## Studio Framework

    1. Pick an active state, district, and tehsil.
    2. Load the published layer inventory and boundary geometries.
    3. Filter by dataset, type, or search term.
    4. Copy the manifest into research code, data catalog notes, or a project brief.

    ```python
    layers = client.generated_layer_urls(
        state="Andhra Pradesh",
        district="Ananthapur",
        tehsil="Amadagur",
    )
    layer_urls = [layer["layer_url"] for layer in layers if layer["layer_type"] == "vector"]
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
            "Paste a CoRE Stack API key above to activate the live layer studio.",
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
    load_location = mo.ui.run_button(label="Load layer studio")
    mo.hstack([tehsil_selector, load_location], widths=[4, 1])
    return load_location, tehsil_selector


@app.cell
def _(load_location, mo):
    is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not is_script_mode and not load_location.value,
        mo.md("Choose a location, then load the layer studio."),
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
                f"Could not load the layer studio.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return generated_layers, mws_geojson, selected_scope, village_geojson


@app.cell
def _(feature_count, generated_layers, mo, mws_geojson, selected_scope, village_geojson):
    mo.hstack(
        [
            mo.stat(label="Scope", value=selected_scope["tehsil"]),
            mo.stat(label="Published layers", value=len(generated_layers)),
            mo.stat(label="MWS", value=feature_count(mws_geojson)),
            mo.stat(label="Villages", value=feature_count(village_geojson)),
        ]
    )
    return


@app.cell
def _(generated_layers, layer_records_to_frame, pl):
    layers_df = layer_records_to_frame(generated_layers)
    layer_type_counts = layers_df.group_by("layer_type").len().sort("len", descending=True)
    dataset_counts = layers_df.group_by("dataset_name").len().sort("len", descending=True)
    layer_types = ["All", *sorted(layers_df["layer_type"].unique().to_list())]
    datasets = ["All", *sorted(layers_df["dataset_name"].unique().to_list())]
    return dataset_counts, datasets, layer_type_counts, layer_types, layers_df


@app.cell
def _(datasets, layer_types, mo):
    search_input = mo.ui.text(
        value="",
        label="Search layers",
        placeholder="dataset, layer, asset path, URL...",
        full_width=True,
    )
    layer_type_filter = mo.ui.dropdown(
        options=layer_types,
        value="All",
        label="Layer type",
        full_width=True,
    )
    dataset_filter = mo.ui.dropdown(
        options=datasets,
        value="All",
        label="Dataset",
        full_width=True,
    )
    mo.vstack([search_input, mo.hstack([layer_type_filter, dataset_filter])])
    return dataset_filter, layer_type_filter, search_input


@app.cell
def _(
    dataset_filter,
    filter_layer_records,
    generated_layers,
    layer_records_to_frame,
    layer_type_filter,
    search_input,
):
    filtered_layer_records = filter_layer_records(
        generated_layers,
        layer_type=layer_type_filter.value,
        dataset=dataset_filter.value,
        term=search_input.value,
    )
    filtered_layers_df = layer_records_to_frame(filtered_layer_records)
    return filtered_layer_records, filtered_layers_df


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
        .properties(height=240)
    )
    dataset_chart = (
        alt.Chart(dataset_counts.head(20))
        .mark_bar()
        .encode(
            y=alt.Y("dataset_name:N", title="Dataset", sort="-x"),
            x=alt.X("len:Q", title="Count"),
            tooltip=["dataset_name", "len"],
        )
        .properties(height=480)
    )
    mo.hstack([type_chart, dataset_chart], widths=[1, 2])
    return


@app.cell
def _(filtered_layers_df, mo):
    mo.vstack(
        [
            mo.md("## Filtered Layer Catalog"),
            mo.ui.dataframe(filtered_layers_df),
        ]
    )
    return


@app.cell
def _(filtered_layer_records, layer_label, mo):
    mo.stop(
        not filtered_layer_records,
        mo.callout("No layers match the current filters.", kind="warn"),
    )
    layer_options = {
        layer_label(record, index): index for index, record in enumerate(filtered_layer_records)
    }
    selected_layer = mo.ui.dropdown(
        options=list(layer_options.keys()),
        value=next(iter(layer_options)),
        label="Inspect one layer",
        full_width=True,
    )
    selected_layer
    return layer_options, selected_layer


@app.cell
def _(
    filtered_layer_records,
    layer_host,
    layer_manifest,
    layer_options,
    mo,
    selected_layer,
):
    selected_record = filtered_layer_records[layer_options[selected_layer.value]]
    layer_url = selected_record.get("layer_url") or ""
    style_url = selected_record.get("style_url") or ""
    gee_asset_path = selected_record.get("gee_asset_path") or ""
    layer_detail = mo.md(
        f"""
        ## Selected Layer

        - Dataset: `{selected_record.get("dataset_name", "")}`
        - Layer: `{selected_record.get("layer_name", "")}`
        - Type: `{selected_record.get("layer_type", "")}`
        - Host: `{layer_host(layer_url)}`
        - Version: `{selected_record.get("layer_version", "")}`
        - Layer URL: [open]({layer_url}) if your credentials/session allow it
        - Style URL: {f"[open]({style_url})" if style_url else "not provided"}
        - GEE asset path: `{gee_asset_path}`
        """
    )
    manifest = mo.md(
        f"""
        ## Current Manifest Preview

        Showing up to 25 filtered records.

        ```json
        {layer_manifest(filtered_layer_records)}
        ```
        """
    )
    mo.vstack([layer_detail, manifest])
    return


@app.cell
def _(folium, geojson_center, mo, mws_geojson, selected_scope, village_geojson):
    map_center = geojson_center(mws_geojson)
    layer_map = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")
    folium.GeoJson(
        village_geojson,
        name="Villages",
        style_function=lambda _: {"color": "#64748b", "weight": 1, "fillOpacity": 0.04},
    ).add_to(layer_map)
    folium.GeoJson(
        mws_geojson,
        name="Micro-watersheds",
        tooltip=folium.GeoJsonTooltip(fields=["uid"], aliases=["MWS uid"]),
        style_function=lambda _: {"color": "#0f766e", "weight": 2, "fillOpacity": 0.08},
    ).add_to(layer_map)
    folium.LayerControl(collapsed=False).add_to(layer_map)
    title = f"{selected_scope['tehsil']}, {selected_scope['district']}, {selected_scope['state']}"
    mo.vstack([mo.md(f"## Geography Frame: {title}"), mo.Html(layer_map._repr_html_())])
    return


if __name__ == "__main__":
    app.run()
