"""Generic API management."""

import pathlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.regions import get_server_url
from bimmer_connected.api.utils import log_to_to_file, raise_for_status_event_handler
from bimmer_connected.const import X_USER_AGENT, CarBrands


@dataclass
class MyBMWClientConfiguration:
    """Stores global settings for MyBMWClient."""

    authentication: MyBMWAuthentication
    log_response_path: Optional[pathlib.Path] = None


class MyBMWClient(httpx.AsyncClient):
    """Async HTTP client based on `httpx.AsyncClient` with automated OAuth token refresh."""

    def __init__(self, config: MyBMWClientConfiguration, *args, brand: CarBrands = None, **kwargs):
        self.config = config

        # Increase timeout
        kwargs["timeout"] = httpx.Timeout(10.0)

        # Set default values
        kwargs["base_url"] = kwargs.get("base_url") or get_server_url(config.authentication.region)
        kwargs["headers"] = kwargs.get("headers") or self.generate_default_header(brand)

        # Register event hooks
        kwargs["event_hooks"] = defaultdict(list, **kwargs.get("event_hooks", {}))

        # Event hook which checks and updates token if required before request is sent
        async def update_request_header(request: httpx.Request):
            request.headers["authorization"] = await self.config.authentication.get_authentication()

        kwargs["event_hooks"]["request"].append(update_request_header)

        # Event hook for logging content to file
        async def log_response(response: httpx.Response):
            content = await response.aread()
            brand = [x for x in [b.value for b in CarBrands] if x in response.request.headers.get("x-user-agent", "")]
            base_file_name = "_".join([response.url.path.split("/")[-1]] + brand)
            log_to_to_file(content, config.log_response_path, base_file_name)  # type: ignore[arg-type]

        if config.log_response_path:
            kwargs["event_hooks"]["response"].append(log_response)

        # Event hook which calls raise_for_status on all requests
        kwargs["event_hooks"]["response"].append(raise_for_status_event_handler)

        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_default_header(brand: CarBrands = None) -> Dict[str, str]:
        """Generate a header for HTTP requests to the server."""
        return {
            "accept": "application/json",
            "accept-language": "en",
            "user-agent": "Dart/2.13 (dart:io)",
            "x-user-agent": X_USER_AGENT.format(brand or CarBrands.BMW),
        }
