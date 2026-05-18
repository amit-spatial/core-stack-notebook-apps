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
    import math
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

    FOCUS_PRESETS = {
        "Balanced NRM planning": {
            "water_stress": 0.30,
            "runoff_opportunity": 0.25,
            "restoration_area": 0.20,
            "community_reach": 0.15,
            "cropping_resilience": 0.10,
        },
        "Water security first": {
            "water_stress": 0.45,
            "runoff_opportunity": 0.25,
            "restoration_area": 0.10,
            "community_reach": 0.10,
            "cropping_resilience": 0.10,
        },
        "Restoration opportunity first": {
            "water_stress": 0.15,
            "runoff_opportunity": 0.20,
            "restoration_area": 0.40,
            "community_reach": 0.10,
            "cropping_resilience": 0.15,
        },
        "Community planning first": {
            "water_stress": 0.20,
            "runoff_opportunity": 0.15,
            "restoration_area": 0.15,
            "community_reach": 0.35,
            "cropping_resilience": 0.15,
        },
    }

    COMPONENT_LABELS = {
        "water_stress": "Water stress",
        "runoff_opportunity": "Runoff opportunity",
        "restoration_area": "Restoration area",
        "community_reach": "Community reach",
        "cropping_resilience": "Cropping resilience",
    }

    ACTIONS = {
        "water_stress": [
            "Check drinking-water and irrigation stress with local users.",
            "Inspect surface-water bodies and recent dry-spell history.",
            "Look for recharge, percolation, and demand-management options.",
        ],
        "runoff_opportunity": [
            "Walk drainage lines and natural depressions before site selection.",
            "Compare candidate sites with CLART, stream order, slope, and catchment layers.",
            "Prioritize field validation where runoff is high but storage is weak.",
        ],
        "restoration_area": [
            "Ground-truth tree-on-slope, shrub-on-slope, and wide-scale restoration patches.",
            "Check grazing, tenure, and protection feasibility with local institutions.",
            "Bundle ecological restoration with livelihood and stewardship planning.",
        ],
        "community_reach": [
            "Use this MWS for Gram Sabha discussion or stewardship planning.",
            "Check intersecting villages, NREGA works, and demand records.",
            "Prepare a short planning note before proposing works.",
        ],
        "cropping_resilience": [
            "Study crop-water demand and cropping intensity before recommending structures.",
            "Check whether low cropping intensity is water, soil, market, or access driven.",
            "Pair remote-sensing signals with farmer interviews.",
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

    def as_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if math.isnan(number) or math.isinf(number):
            return default
        return number

    def as_count(value: Any) -> int:
        if isinstance(value, list | tuple | set):
            return len(value)
        if value in (None, ""):
            return 0
        return 1

    def normalize(values: list[float]) -> list[float]:
        if not values:
            return []
        low = min(values)
        high = max(values)
        if math.isclose(low, high):
            return [0.5 for _ in values]
        return [(value - low) / (high - low) for value in values]

    def build_candidate_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for record in records:
            kharif = as_float(record.get("avg_wsr_ratio_kharif"))
            rabi = as_float(record.get("avg_wsr_ratio_rabi"))
            zaid = as_float(record.get("avg_wsr_ratio_zaid"))
            villages = as_count(record.get("mws_intersect_villages"))
            swb_count = as_count(record.get("mws_intersect_swb"))
            rows.append(
                {
                    "mws_id": str(record.get("mws_id", "")),
                    "avg_precipitation": as_float(record.get("avg_precipitation")),
                    "avg_runoff": as_float(record.get("avg_runoff")),
                    "dry_spells": as_float(record.get("avg_number_dry_spell")),
                    "max_wsr": max(kharif, rabi, zaid),
                    "drought_category": as_float(record.get("drought_category")),
                    "restoration_ha": (
                        as_float(record.get("area_wide_scale_restoration"))
                        + as_float(record.get("area_protection"))
                        + as_float(record.get("area_tree_on_slope"))
                        + as_float(record.get("area_shrubs_on_slope"))
                    ),
                    "crop_plain_ha": as_float(record.get("area_crops_on_plain")),
                    "cropping_intensity": as_float(record.get("cropping_intensity_avg")),
                    "village_count": villages,
                    "nrega_assets": as_float(record.get("total_nrega_assets")),
                    "surface_water_bodies": swb_count,
                    "terraincluster_id": as_float(record.get("terraincluster_id")),
                    "aquifer_class": as_float(record.get("aquifer_class")),
                    "soge_class": as_float(record.get("soge_class")),
                }
            )
        return rows

    def score_candidates(
        rows: list[dict[str, Any]],
        weights: dict[str, float],
    ) -> list[dict[str, Any]]:
        raw_components = {
            "water_stress": [
                row["max_wsr"] + row["dry_spells"] + row["drought_category"] for row in rows
            ],
            "runoff_opportunity": [
                row["avg_runoff"] + (0.25 * row["surface_water_bodies"]) for row in rows
            ],
            "restoration_area": [row["restoration_ha"] for row in rows],
            "community_reach": [
                row["village_count"] + math.log1p(row["nrega_assets"]) for row in rows
            ],
            "cropping_resilience": [
                row["crop_plain_ha"] * max(0.0, 1.5 - row["cropping_intensity"]) for row in rows
            ],
        }
        normalized = {name: normalize(values) for name, values in raw_components.items()}
        total_weight = sum(max(weight, 0.0) for weight in weights.values()) or 1.0

        scored = []
        for index, row in enumerate(rows):
            component_scores = {
                name: normalized[name][index] for name in raw_components if normalized[name]
            }
            priority_score = (
                sum(component_scores[name] * weights.get(name, 0.0) for name in component_scores)
                / total_weight
            )
            driver = max(component_scores, key=component_scores.get)
            scored.append(
                {
                    **row,
                    **{
                        f"{name}_score": round(value, 3)
                        for name, value in component_scores.items()
                    },
                    "priority_score": round(priority_score, 3),
                    "dominant_driver": driver,
                    "action_family": COMPONENT_LABELS[driver],
                    "recommended_action": ACTIONS[driver][0],
                }
            )

        scored.sort(key=lambda row: row["priority_score"], reverse=True)
        for rank, row in enumerate(scored, start=1):
            row["rank"] = rank
        return scored

    def subset_geojson_by_uid(geojson: dict[str, Any], uids: set[str]) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [
                feature
                for feature in geojson.get("features", [])
                if str(feature.get("properties", {}).get("uid")) in uids
            ],
        }

    def score_color(score: float) -> str:
        if score >= 0.75:
            return "#b91c1c"
        if score >= 0.55:
            return "#f97316"
        if score >= 0.35:
            return "#facc15"
        return "#22c55e"

    def planning_brief(
        row: dict[str, Any],
        scope: dict[str, str],
        weights: dict[str, float],
    ) -> str:
        actions = ACTIONS.get(row["dominant_driver"], [])
        action_lines = "\n".join(f"- {action}" for action in actions)
        weight_lines = "\n".join(
            f"- {COMPONENT_LABELS[key]}: {value:.2f}" for key, value in weights.items()
        )
        return f"""# MWS Planning Brief

Location: {scope["tehsil"]}, {scope["district"]}, {scope["state"]}
MWS uid: {row["mws_id"]}
Priority rank: {row["rank"]}
Priority score: {row["priority_score"]:.3f}
Dominant driver: {row["action_family"]}

## Evidence Snapshot

- Water stress score: {row["water_stress_score"]:.3f}
- Runoff opportunity score: {row["runoff_opportunity_score"]:.3f}
- Restoration area score: {row["restoration_area_score"]:.3f}
- Community reach score: {row["community_reach_score"]:.3f}
- Cropping resilience score: {row["cropping_resilience_score"]:.3f}
- Intersecting villages: {row["village_count"]}
- NREGA assets: {row["nrega_assets"]:.0f}
- Surface water bodies: {row["surface_water_bodies"]}

## Current Weights

{weight_lines}

## Recommended Field Checks

{action_lines}

## Caveat

This is a transparent screening score, not a final site decision. Use it to prioritize
field validation, community discussion, and more detailed hydrological or CLART analysis.
"""

    try:
        repo_root = Path(__file__).resolve().parents[1]
    except NameError:
        repo_root = Path.cwd()

    return (
        ACTIONS,
        COMPONENT_LABELS,
        CoreStackPublicAPIError,
        CoreStackPublicClient,
        CoreStackSettings,
        FOCUS_PRESETS,
        alt,
        build_candidate_rows,
        describe_api_exception,
        folium,
        geojson_center,
        json,
        mo,
        planning_brief,
        pl,
        property_values,
        repo_root,
        score_candidates,
        score_color,
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
            # CoRE Stack Action Planner

            This app turns CoRE Stack public API outputs into a transparent planning
            workbench. It scans micro-watersheds, builds a weighted priority score,
            maps candidates, and creates a field-check brief.
            """),
            mo.callout(
                """
                This is closer to CLART or Commons Connect style reasoning than a data
                catalog: use the weights, map, and recommended checks to ask where a
                stewardship team should investigate first.

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
    ## Method Frame

    The planner combines five evidence families:

    - water stress from WSR ratios, drought category, and dry spells
    - runoff opportunity from runoff and surface-water-body context
    - restoration area from protection, tree-on-slope, shrub-on-slope, and wide-scale restoration
    - community reach from villages and NREGA assets
    - cropping resilience from crop area and lower cropping intensity

    ```python
    priority_score = weighted_average(
        water_stress,
        runoff_opportunity,
        restoration_area,
        community_reach,
        cropping_resilience,
    )
    ```

    Treat the score as a screening tool. It should guide field visits and community
    discussion, not replace them.
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
            "Paste a CoRE Stack API key above to activate the action planner.",
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
def _(FOCUS_PRESETS, mo, tehsil_names):
    tehsil_selector = mo.ui.dropdown(
        options=tehsil_names,
        value=tehsil_names[0],
        label="Tehsil / block",
        full_width=True,
    )
    focus_selector = mo.ui.dropdown(
        options=list(FOCUS_PRESETS.keys()),
        value="Balanced NRM planning",
        label="Planning focus",
        full_width=True,
    )
    load_location = mo.ui.run_button(label="Load planning geography")
    mo.vstack([mo.hstack([tehsil_selector, focus_selector]), load_location])
    return focus_selector, load_location, tehsil_selector


@app.cell
def _(load_location, mo):
    _is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not _is_script_mode and not load_location.value,
        mo.md("Choose a location and planning focus, then load the planning geography."),
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
                f"Could not load planning geography.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return generated_layers, mws_geojson, selected_scope, village_geojson


@app.cell
def _(mo, mws_geojson, property_values):
    mws_uids = property_values(mws_geojson, "uid")
    mo.stop(
        not mws_uids,
        mo.callout("No MWS features were returned for this location.", kind="warn"),
    )
    scan_limit = mo.ui.slider(
        start=3,
        stop=min(40, len(mws_uids)),
        step=1,
        value=min(15, len(mws_uids)),
        label="MWS scan limit",
    )
    scan_button = mo.ui.run_button(label="Scan candidates")
    mo.vstack(
        [
            mo.callout(
                "Scanning makes one KYL indicator request per MWS. Start small, then expand.",
                kind="neutral",
            ),
            mo.hstack([scan_limit, scan_button]),
        ]
    )
    return mws_uids, scan_button, scan_limit


@app.cell
def _(FOCUS_PRESETS, focus_selector, mo):
    defaults = FOCUS_PRESETS[focus_selector.value]
    water_weight = mo.ui.slider(
        0,
        1,
        value=defaults["water_stress"],
        step=0.05,
        label="Water stress weight",
    )
    runoff_weight = mo.ui.slider(
        0,
        1,
        value=defaults["runoff_opportunity"],
        step=0.05,
        label="Runoff opportunity weight",
    )
    restoration_weight = mo.ui.slider(
        0,
        1,
        value=defaults["restoration_area"],
        step=0.05,
        label="Restoration area weight",
    )
    community_weight = mo.ui.slider(
        0,
        1,
        value=defaults["community_reach"],
        step=0.05,
        label="Community reach weight",
    )
    crop_weight = mo.ui.slider(
        0,
        1,
        value=defaults["cropping_resilience"],
        step=0.05,
        label="Cropping resilience weight",
    )
    mo.vstack(
        [
            mo.md("## Planning Weights"),
            mo.hstack([water_weight, runoff_weight, restoration_weight]),
            mo.hstack([community_weight, crop_weight]),
        ]
    )
    return (
        community_weight,
        crop_weight,
        restoration_weight,
        runoff_weight,
        water_weight,
    )


@app.cell
def _(
    CoreStackPublicAPIError,
    client,
    describe_api_exception,
    mo,
    mws_uids,
    scan_button,
    scan_limit,
    selected_scope,
):
    _is_script_mode = mo.app_meta().mode == "script"
    mo.stop(
        not _is_script_mode and not scan_button.value,
        mo.md("Set weights, then scan candidate MWSs."),
    )
    candidate_uids = mws_uids[: scan_limit.value]
    kyl_records = []
    try:
        for _uid in candidate_uids:
            payload = client.mws_kyl_indicators(**selected_scope, mws_id=_uid)
            if payload:
                kyl_records.append(payload[0])
    except CoreStackPublicAPIError as exc:
        mo.stop(
            True,
            mo.callout(
                f"Could not scan MWS indicators.\n\n{describe_api_exception(exc)}",
                kind="danger",
            ),
        )
    return candidate_uids, kyl_records


@app.cell
def _(
    build_candidate_rows,
    community_weight,
    crop_weight,
    kyl_records,
    pl,
    restoration_weight,
    runoff_weight,
    score_candidates,
    water_weight,
):
    planning_weights = {
        "water_stress": water_weight.value,
        "runoff_opportunity": runoff_weight.value,
        "restoration_area": restoration_weight.value,
        "community_reach": community_weight.value,
        "cropping_resilience": crop_weight.value,
    }
    raw_rows = build_candidate_rows(kyl_records)
    scored_rows = score_candidates(raw_rows, planning_weights)
    candidate_df = pl.DataFrame(scored_rows) if scored_rows else pl.DataFrame()
    return candidate_df, planning_weights, scored_rows


@app.cell
def _(candidate_df, mo, scored_rows):
    mo.stop(
        not scored_rows,
        mo.callout("No candidate indicator rows were returned.", kind="warn"),
    )
    visible_columns = [
        "rank",
        "mws_id",
        "priority_score",
        "action_family",
        "recommended_action",
        "water_stress_score",
        "runoff_opportunity_score",
        "restoration_area_score",
        "community_reach_score",
        "cropping_resilience_score",
        "village_count",
        "nrega_assets",
        "surface_water_bodies",
    ]
    mo.vstack(
        [
            mo.md("## Candidate Ranking"),
            mo.ui.dataframe(candidate_df.select(visible_columns)),
        ]
    )
    return


@app.cell
def _(alt, candidate_df, mo):
    score_chart = (
        alt.Chart(candidate_df.head(20))
        .mark_bar()
        .encode(
            y=alt.Y("mws_id:N", title="MWS uid", sort="-x"),
            x=alt.X("priority_score:Q", title="Priority score"),
            color=alt.Color("action_family:N", title="Dominant driver"),
            tooltip=[
                "rank",
                "mws_id",
                "priority_score",
                "action_family",
                "recommended_action",
            ],
        )
        .properties(height=420)
    )
    mo.vstack([mo.md("## Score Drivers"), score_chart])
    return


@app.cell
def _(mo, scored_rows):
    candidate_options = {
        f"#{row['rank']} | {row['mws_id']} | {row['action_family']}": row["mws_id"]
        for row in scored_rows
    }
    selected_candidate = mo.ui.dropdown(
        options=list(candidate_options.keys()),
        value=next(iter(candidate_options)),
        label="Inspect candidate",
        full_width=True,
    )
    selected_candidate
    return candidate_options, selected_candidate


@app.cell
def _(candidate_options, scored_rows, selected_candidate):
    selected_mws_id = candidate_options[selected_candidate.value]
    selected_row = next(row for row in scored_rows if row["mws_id"] == selected_mws_id)
    top_uids = {row["mws_id"] for row in scored_rows[:10]}
    return selected_mws_id, selected_row, top_uids


@app.cell
def _(
    COMPONENT_LABELS,
    folium,
    geojson_center,
    mo,
    mws_geojson,
    score_color,
    scored_rows,
    selected_mws_id,
    selected_scope,
    subset_geojson_by_uid,
    top_uids,
    village_geojson,
):
    map_center = geojson_center(mws_geojson)
    planner_map = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB positron")
    score_by_uid = {row["mws_id"]: row for row in scored_rows}

    folium.GeoJson(
        village_geojson,
        name="Villages",
        style_function=lambda _: {"color": "#64748b", "weight": 1, "fillOpacity": 0.04},
    ).add_to(planner_map)

    folium.GeoJson(
        mws_geojson,
        name="All MWS",
        style_function=lambda _: {"color": "#94a3b8", "weight": 1, "fillOpacity": 0.02},
    ).add_to(planner_map)

    top_geojson = subset_geojson_by_uid(mws_geojson, top_uids)

    def candidate_style(feature):
        _uid = str(feature.get("properties", {}).get("uid"))
        row = score_by_uid.get(_uid, {})
        weight = 4 if _uid == selected_mws_id else 2
        color = "#111827" if _uid == selected_mws_id else score_color(
            row.get("priority_score", 0)
        )
        return {
            "color": color,
            "weight": weight,
            "fillColor": score_color(row.get("priority_score", 0)),
            "fillOpacity": 0.28 if _uid == selected_mws_id else 0.18,
        }

    for feature in top_geojson.get("features", []):
        _feature_uid = str(feature.get("properties", {}).get("uid"))
        row = score_by_uid.get(_feature_uid, {})
        feature.setdefault("properties", {})
        feature["properties"]["rank"] = row.get("rank")
        feature["properties"]["priority_score"] = row.get("priority_score")
        feature["properties"]["action_family"] = row.get("action_family")
        feature["properties"]["dominant_driver"] = COMPONENT_LABELS.get(
            row.get("dominant_driver", ""),
            "",
        )

    folium.GeoJson(
        top_geojson,
        name="Top candidates",
        tooltip=folium.GeoJsonTooltip(
            fields=["uid", "rank", "priority_score", "action_family"],
            aliases=["MWS uid", "Rank", "Priority score", "Action family"],
        ),
        style_function=candidate_style,
    ).add_to(planner_map)

    folium.LayerControl(collapsed=False).add_to(planner_map)
    title = f"{selected_scope['tehsil']}, {selected_scope['district']}, {selected_scope['state']}"
    mo.vstack([mo.md(f"## Planning Map: {title}"), mo.Html(planner_map._repr_html_())])
    return


@app.cell
def _(ACTIONS, COMPONENT_LABELS, mo, selected_row):
    action_items = ACTIONS[selected_row["dominant_driver"]]
    action_markdown = "\n".join(f"- {item}" for item in action_items)
    mo.vstack(
        [
            mo.md(f"## Candidate Brief: `{selected_row['mws_id']}`"),
            mo.callout(
                f"Dominant driver: {COMPONENT_LABELS[selected_row['dominant_driver']]}. "
                f"Priority score: {selected_row['priority_score']:.3f}.",
                kind="success",
            ),
            mo.md(
                f"""
                ### Recommended field checks

                {action_markdown}

                ### Why this candidate surfaced

                - Water stress score: `{selected_row["water_stress_score"]:.3f}`
                - Runoff opportunity score: `{selected_row["runoff_opportunity_score"]:.3f}`
                - Restoration area score: `{selected_row["restoration_area_score"]:.3f}`
                - Community reach score: `{selected_row["community_reach_score"]:.3f}`
                - Cropping resilience score: `{selected_row["cropping_resilience_score"]:.3f}`
                """
            ),
        ]
    )
    return


@app.cell
def _(json, mo, planning_brief, planning_weights, selected_row, selected_scope):
    brief = planning_brief(selected_row, selected_scope, planning_weights)
    machine_readable = json.dumps(
        {
            "scope": selected_scope,
            "selected_candidate": selected_row,
            "weights": planning_weights,
        },
        indent=2,
    )
    mo.vstack(
        [
            mo.md("## Exportable Reasoning Trail"),
            mo.md(f"```markdown\n{brief}\n```"),
            mo.md("### JSON payload"),
            mo.md(f"```json\n{machine_readable}\n```"),
        ]
    )
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
