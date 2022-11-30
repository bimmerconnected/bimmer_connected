"""Generic API management."""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

import httpx

from bimmer_connected.api.authentication import MyBMWAuthentication
from bimmer_connected.api.regions import get_app_version, get_server_url
from bimmer_connected.api.utils import anonymize_response, get_correlation_id
from bimmer_connected.const import HTTPX_TIMEOUT, USER_AGENT, X_USER_AGENT, CarBrands
from bimmer_connected.models import AnonymizedResponse, GPSPosition

RESPONSE_STORE: Deque[AnonymizedResponse] = deque(maxlen=10)


@dataclass
class MyBMWClientConfiguration:
    """Stores global settings for MyBMWClient."""

    authentication: MyBMWAuthentication
    log_responses: Optional[bool] = False
    observer_position: Optional[GPSPosition] = None
    use_metric_units: Optional[bool] = True

    def set_log_responses(self, log_responses: bool) -> None:
        """Set if responses are logged and clear response store."""

        self.log_responses = log_responses
        RESPONSE_STORE.clear()


class MyBMWClient(httpx.AsyncClient):
    """Async HTTP client based on `httpx.AsyncClient` with automated OAuth token refresh."""

    def __init__(self, config: MyBMWClientConfiguration, *args, brand: Optional[CarBrands] = None, **kwargs):
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

        # Event hook for logging content
        async def log_response(response: httpx.Response):
            await response.aread()
            RESPONSE_STORE.append(anonymize_response(response))

        if config.log_responses:
            kwargs["event_hooks"]["response"].append(log_response)

        # Event hook which calls raise_for_status on all requests
        async def raise_for_status_event_handler(response: httpx.Response):
            """Event handler that automatically raises HTTPStatusErrors when attached.

            Will only raise on 4xx/5xx errors (but not 401!) and not raise on 3xx.
            """
            if response.is_error and response.status_code not in [401, 429]:
                await response.aread()
                response.raise_for_status()

        kwargs["event_hooks"]["response"].append(raise_for_status_event_handler)

        super().__init__(*args, **kwargs)

    def generate_default_header(self, brand: Optional[CarBrands] = None) -> Dict[str, str]:
        """Generate a header for HTTP requests to the server."""
        return {
            "accept": "application/json",
            "accept-language": "en",
            "user-agent": USER_AGENT,
            "x-user-agent": X_USER_AGENT.format(
                brand=(brand or CarBrands.BMW).value,
                app_version=get_app_version(self.config.authentication.region),
                region=self.config.authentication.region.value,
            ),
            **get_correlation_id(),
            "bmw-units-preferences": "d=KM;v=L" if self.config.use_metric_units else "d=MI;v=G",
            "24-hour-format": "true",
        }
