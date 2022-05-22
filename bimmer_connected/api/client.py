"""Generic API management."""

import pathlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.regions import get_server_url
from bimmer_connected.api.utils import get_correlation_id, log_to_to_file
from bimmer_connected.const import HTTPX_TIMEOUT, USER_AGENT, X_USER_AGENT, CarBrands


@dataclass
class MyBMWClientConfiguration:
    """Stores global settings for MyBMWClient."""

    authentication: MyBMWAuthentication
    log_response_path: Optional[pathlib.Path] = None


class MyBMWClient(httpx.AsyncClient):
    """Async HTTP client based on `httpx.AsyncClient` with automated OAuth token refresh."""

    def __init__(self, config: MyBMWClientConfiguration, *args, brand: CarBrands = None, **kwargs):
        self.config = config

        # Add authentication
        kwargs["auth"] = self.config.authentication

        # Increase timeout
        kwargs["timeout"] = httpx.Timeout(HTTPX_TIMEOUT)

        # Set default values
        kwargs["base_url"] = kwargs.get("base_url") or get_server_url(config.authentication.region)
        kwargs["headers"] = kwargs.get("headers") or self.generate_default_header(brand)

        # Register event hooks
        kwargs["event_hooks"] = defaultdict(list, **kwargs.get("event_hooks", {}))

        # Event hook for logging content to file
        async def log_response(response: httpx.Response):
            content = await response.aread()
            brand = [x for x in [b.value for b in CarBrands] if x in response.request.headers.get("x-user-agent", "")]
            base_file_name = "_".join([response.url.path.split("/")[-1]] + brand)
            log_to_to_file(content, config.log_response_path, base_file_name)  # type: ignore[arg-type]

        if config.log_response_path:
            kwargs["event_hooks"]["response"].append(log_response)

        # Event hook which calls raise_for_status on all requests
        async def raise_for_status_event_handler(response: httpx.Response):
            """Event handler that automatically raises HTTPStatusErrors when attached.

            Will only raise on 4xx/5xx errors (but not 401!) and not raise on 3xx.
            """
            if response.is_error and response.status_code != 401:
                await response.aread()
                response.raise_for_status()

        kwargs["event_hooks"]["response"].append(raise_for_status_event_handler)

        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_default_header(brand: CarBrands = None) -> Dict[str, str]:
        """Generate a header for HTTP requests to the server."""
        return {
            "accept": "application/json",
            "accept-language": "en",
            "user-agent": USER_AGENT,
            "x-user-agent": X_USER_AGENT.format(brand or CarBrands.BMW),
            **get_correlation_id(),
        }
