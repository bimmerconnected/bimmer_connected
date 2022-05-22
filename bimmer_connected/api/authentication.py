"""Authentication management for BMW APIs."""

import asyncio
import base64
import datetime
import logging
import math
from collections import defaultdict
from typing import AsyncGenerator, Generator, Optional
from uuid import uuid4

import httpx
import jwt
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

from bimmer_connected.api.regions import Regions, get_aes_keys, get_ocp_apim_key, get_server_url
from bimmer_connected.api.utils import (
    create_s256_code_challenge,
    generate_token,
    get_correlation_id,
    handle_http_status_error,
)
from bimmer_connected.const import (
    AUTH_CHINA_LOGIN_URL,
    AUTH_CHINA_PUBLIC_KEY_URL,
    AUTH_CHINA_TOKEN_URL,
    HTTPX_TIMEOUT,
    OAUTH_CONFIG_URL,
    USER_AGENT,
    X_USER_AGENT,
)

EXPIRES_AT_OFFSET = datetime.timedelta(seconds=HTTPX_TIMEOUT * 2)

_LOGGER = logging.getLogger(__name__)


class MyBMWAuthentication(httpx.Auth):
    """Authentication for MyBMW API."""

    # pylint: disable=too-many-arguments,too-many-instance-attributes
    def __init__(
        self,
        username: str,
        password: str,
        region: Regions,
        access_token: Optional[str] = None,
        expires_at: Optional[datetime.datetime] = None,
        refresh_token: Optional[str] = None,
    ):
        self.username: str = username
        self.password: str = password
        self.region: Regions = region
        self.access_token: Optional[str] = access_token
        self.expires_at: Optional[datetime.datetime] = expires_at
        self.refresh_token: Optional[str] = refresh_token
        self.session_id: str = str(uuid4())
        self._lock: Optional[asyncio.Lock] = None

    @property
    def login_lock(self) -> asyncio.Lock:
        """Makes sure that there is a lock in the current event loop."""
        if not self._lock:
            self._lock = asyncio.Lock()
        return self._lock

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        raise RuntimeError("Cannot use a async authentication class with httpx.Client")

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        # Get an access token on first call
        async with self.login_lock:
            if not self.access_token:
                await self.login()
        request.headers["authorization"] = f"Bearer {self.access_token}"
        request.headers["bmw-session-id"] = self.session_id

        # Try getting a response
        response: httpx.Response = (yield request)

        if response.status_code == 401:
            async with self.login_lock:
                _LOGGER.debug("Received unauthorized response, refreshing token.")
                await self.login()
            request.headers["authorization"] = f"Bearer {self.access_token}"
            request.headers["bmw-session-id"] = self.session_id
            yield request

    async def login(self) -> None:
        """Get a valid OAuth token."""
        token_data = {}
        if self.region in [Regions.NORTH_AMERICA, Regions.REST_OF_WORLD]:
            # Try logging in with refresh token first
            if self.refresh_token:
                token_data = await self._refresh_token_row_na()
            if not token_data:
                # clear refresh token as precaution
                self.refresh_token = None
                token_data = await self._login_row_na()
            token_data["expires_at"] = token_data["expires_at"] - EXPIRES_AT_OFFSET

        elif self.region in [Regions.CHINA]:
            # Try logging in with refresh token first
            if self.refresh_token:
                token_data = await self._refresh_token_china()
            if not token_data:
                # clear refresh token as precaution
                self.refresh_token = None
                token_data = await self._login_china()
            token_data["expires_at"] = token_data["expires_at"] - EXPIRES_AT_OFFSET

        self.access_token = token_data["access_token"]
        self.expires_at = token_data["expires_at"]
        self.refresh_token = token_data["refresh_token"]

    async def _login_row_na(self):  # pylint: disable=too-many-locals
        """Login to Rest of World and North America."""
        try:
            async with MyBMWLoginClient(region=self.region) as client:
                _LOGGER.debug("Authenticating with MyBMW flow for North America & Rest of World.")

                # Get OAuth2 settings from BMW API
                r_oauth_settings = await client.get(
                    OAUTH_CONFIG_URL,
                    headers={
                        "ocp-apim-subscription-key": get_ocp_apim_key(self.region),
                        "bmw-session-id": self.session_id,
                        **get_correlation_id(),
                    },
                )
                oauth_settings = r_oauth_settings.json()

                # Generate OAuth2 Code Challenge + State
                code_verifier = generate_token(86)
                code_challenge = create_s256_code_challenge(code_verifier)

                state = generate_token(22)

                # Set up authenticate endpoint
                authenticate_url = oauth_settings["tokenEndpoint"].replace("/token", "/authenticate")
                oauth_base_values = {
                    "client_id": oauth_settings["clientId"],
                    "response_type": "code",
                    "redirect_uri": oauth_settings["returnUrl"],
                    "state": state,
                    "nonce": "login_nonce",
                    "scope": " ".join(oauth_settings["scopes"]),
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                }

                # Call authenticate endpoint first time (with user/pw) and get authentication
                response = await client.post(
                    authenticate_url,
                    data=dict(
                        oauth_base_values,
                        **{
                            "grant_type": "authorization_code",
                            "username": self.username,
                            "password": self.password,
                        },
                    ),
                )
                authorization = httpx.URL(response.json()["redirect_to"]).params["authorization"]

                # With authorization, call authenticate endpoint second time to get code
                response = await client.post(
                    authenticate_url,
                    data=dict(oauth_base_values, **{"authorization": authorization}),
                )
                code = response.next_request.url.params["code"]

                # With code, get token
                current_utc_time = datetime.datetime.utcnow()
                response = await client.post(
                    oauth_settings["tokenEndpoint"],
                    data={
                        "code": code,
                        "code_verifier": code_verifier,
                        "redirect_uri": oauth_settings["returnUrl"],
                        "grant_type": "authorization_code",
                    },
                    auth=(oauth_settings["clientId"], oauth_settings["clientSecret"]),
                )
                response_json = response.json()

                expiration_time = int(response_json["expires_in"])
                expires_at = current_utc_time + datetime.timedelta(seconds=expiration_time)

        except httpx.HTTPStatusError as ex:
            handle_http_status_error(ex, "Authentication", _LOGGER)

        return {
            "access_token": response_json["access_token"],
            "expires_at": expires_at,
            "refresh_token": response_json["refresh_token"],
        }

    async def _refresh_token_row_na(self):
        """Login to Rest of World and North America using existing refresh_token."""
        try:
            async with MyBMWLoginClient(region=self.region) as client:
                _LOGGER.debug("Authenticating with refresh token for North America & Rest of World.")

                # Get OAuth2 settings from BMW API
                r_oauth_settings = await client.get(
                    OAUTH_CONFIG_URL,
                    headers={
                        "ocp-apim-subscription-key": get_ocp_apim_key(self.region),
                        "bmw-session-id": self.session_id,
                        **get_correlation_id(),
                    },
                )
                oauth_settings = r_oauth_settings.json()

                # With code, get token
                current_utc_time = datetime.datetime.utcnow()
                response = await client.post(
                    oauth_settings["tokenEndpoint"],
                    data={
                        "scope": " ".join(oauth_settings["scopes"]),
                        "redirect_uri": oauth_settings["returnUrl"],
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                    auth=(oauth_settings["clientId"], oauth_settings["clientSecret"]),
                )
                response_json = response.json()

                expiration_time = int(response_json["expires_in"])
                expires_at = current_utc_time + datetime.timedelta(seconds=expiration_time)

        except httpx.HTTPStatusError as ex:
            _LOGGER.debug("Unable to get access token using refresh token.")
            handle_http_status_error(ex, "Authentication", _LOGGER, debug=True)
            return {}

        return {
            "access_token": response_json["access_token"],
            "expires_at": expires_at,
            "refresh_token": response_json["refresh_token"],
        }

    async def _login_china(self):
        try:
            async with MyBMWLoginClient(region=self.region) as client:
                _LOGGER.debug("Authenticating with MyBMW flow for China.")

                # Get current RSA public certificate & use it to encrypt password
                response = await client.get(
                    AUTH_CHINA_PUBLIC_KEY_URL,
                )
                pem_public_key = response.json()["data"]["value"]

                public_key = RSA.import_key(pem_public_key)
                cipher_rsa = PKCS1_v1_5.new(public_key)
                encrypted = cipher_rsa.encrypt(self.password.encode())
                pw_encrypted = base64.b64encode(encrypted).decode("UTF-8")

                cipher_aes = AES.new(**get_aes_keys(self.region), mode=AES.MODE_CBC)
                nonce = f"{self.username}|{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%fZ')}".encode()

                # Get token
                response = await client.post(
                    AUTH_CHINA_LOGIN_URL,
                    headers={"x-login-nonce": base64.b64encode(cipher_aes.encrypt(pad(nonce, 16))).decode()},
                    json={"mobile": self.username, "password": pw_encrypted},
                )
                response_json = response.json()["data"]

                decoded_token = jwt.decode(
                    response_json["access_token"], algorithms=["HS256"], options={"verify_signature": False}
                )

        except httpx.HTTPStatusError as ex:
            handle_http_status_error(ex, "Authentication", _LOGGER)

        return {
            "access_token": response_json["access_token"],
            "expires_at": datetime.datetime.utcfromtimestamp(decoded_token["exp"]),
            "refresh_token": response_json["refresh_token"],
        }

    async def _refresh_token_china(self):
        try:
            async with MyBMWLoginClient(region=self.region) as client:
                _LOGGER.debug("Authenticating with refresh token for China.")

                current_utc_time = datetime.datetime.utcnow()

                # Try logging in using refresh_token
                response = await client.post(
                    AUTH_CHINA_TOKEN_URL,
                    data={
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                response_json = response.json()

                expiration_time = int(response_json["expires_in"])
                expires_at = current_utc_time + datetime.timedelta(seconds=expiration_time)

        except httpx.HTTPStatusError as ex:
            _LOGGER.debug("Unable to get access token using refresh token.")
            handle_http_status_error(ex, "Authentication", _LOGGER, debug=True)
            return {}

        return {
            "access_token": response_json["access_token"],
            "expires_at": expires_at,
            "refresh_token": response_json["refresh_token"],
        }


class MyBMWLoginClient(httpx.AsyncClient):
    """Async HTTP client based on `httpx.AsyncClient` with automated OAuth token refresh."""

    def __init__(self, *args, **kwargs):
        # Increase timeout
        kwargs["timeout"] = httpx.Timeout(HTTPX_TIMEOUT)

        kwargs["auth"] = MyBMWLoginRetry()

        # Set default values
        kwargs["base_url"] = get_server_url(kwargs.pop("region"))
        kwargs["headers"] = {"user-agent": USER_AGENT, "x-user-agent": X_USER_AGENT.format("bmw")}

        # Register event hooks
        kwargs["event_hooks"] = defaultdict(list, **kwargs.get("event_hooks", {}))

        # Event hook which calls raise_for_status on all requests
        async def raise_for_status_event_handler(response: httpx.Response):
            """Event handler that automatically raises HTTPStatusErrors when attached.

            Will only raise on 4xx/5xx errors (but not on 429) and not raise on 3xx.
            """
            if response.is_error and not response.status_code == 429:
                await response.aread()
                response.raise_for_status()

        kwargs["event_hooks"]["response"].append(raise_for_status_event_handler)

        super().__init__(*args, **kwargs)


class MyBMWLoginRetry(httpx.Auth):
    """httpx.Auth used as workaround to retry & sleep on 429 Too Many Requests."""

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        raise RuntimeError("Cannot use a async authentication class with httpx.Client")

    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        # Try getting a response
        response: httpx.Response = (yield request)

        for _ in range(5):
            if response.status_code == 429:
                await response.aread()
                wait_time = math.ceil(
                    next(iter([int(i) for i in response.json().get("message", "") if i.isdigit()]), 2) * 1.25
                )
                _LOGGER.debug("Sleeping %s seconds due to 429 Too Many Requests", wait_time)
                await asyncio.sleep(wait_time)
                response = yield request
        if response.status_code == 429:
            await response.aread()
            response.raise_for_status()
