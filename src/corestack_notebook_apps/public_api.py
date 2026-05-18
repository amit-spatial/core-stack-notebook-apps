from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .config import CoreStackSettings

Json = dict[str, Any] | list[Any]


class CoreStackPublicAPIError(RuntimeError):
    """Raised when the CoRE Stack public API returns an error response."""


@dataclass(frozen=True)
class CoreStackPublicClient:
    api_key: str
    base_url: str = "https://geoserver.core-stack.org/api/v1"
    timeout: float = 60.0

    @classmethod
    def from_settings(cls, settings: CoreStackSettings) -> CoreStackPublicClient:
        if not settings.public_api_key:
            msg = "No CoRE Stack public API key found."
            raise CoreStackPublicAPIError(msg)
        return cls(
            api_key=settings.public_api_key,
            base_url=settings.public_api_base_url,
        )

    def get(self, path: str, **params: str | int | float | bool | None) -> Json:
        clean_params = {key: value for key, value in params.items() if value is not None}
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }

        try:
            response = httpx.get(url, params=clean_params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            msg = f"{exc.response.status_code} response from {url}: {detail}"
            raise CoreStackPublicAPIError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Could not reach {url}: {exc}"
            raise CoreStackPublicAPIError(msg) from exc

        return response.json()

    def active_locations(self) -> list[dict[str, Any]]:
        payload = self.get("get_active_locations/")
        if not isinstance(payload, list):
            msg = "Expected active locations to be a list."
            raise CoreStackPublicAPIError(msg)
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
            msg = "Expected generated layer URLs to be a list."
            raise CoreStackPublicAPIError(msg)
        return payload

    def mws_geometries(self, *, state: str, district: str, tehsil: str) -> dict[str, Any]:
        payload = self.get(
            "get_mws_geometries/",
            state=state,
            district=district,
            tehsil=tehsil,
        )
        if not isinstance(payload, dict):
            msg = "Expected MWS geometries to be a GeoJSON object."
            raise CoreStackPublicAPIError(msg)
        return payload

    def village_geometries(self, *, state: str, district: str, tehsil: str) -> dict[str, Any]:
        payload = self.get(
            "get_village_geometries/",
            state=state,
            district=district,
            tehsil=tehsil,
        )
        if not isinstance(payload, dict):
            msg = "Expected village geometries to be a GeoJSON object."
            raise CoreStackPublicAPIError(msg)
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
            msg = "Expected MWS data to be a dictionary."
            raise CoreStackPublicAPIError(msg)
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
            msg = "Expected MWS KYL indicators to be a list."
            raise CoreStackPublicAPIError(msg)
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
            msg = "Expected MWS report response to be a dictionary."
            raise CoreStackPublicAPIError(msg)
        return payload

