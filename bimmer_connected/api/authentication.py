"""Authentication management for BMW APIs."""

import asyncio
import base64
import datetime
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from bimmer_connected.api.regions import Regions, get_ocp_apim_key, get_server_url
from bimmer_connected.api.utils import (
    create_s256_code_challenge,
    generate_token,
    handle_http_status_error,
    raise_for_status_event_handler,
)
from bimmer_connected.const import AUTH_CHINA_LOGIN_URL, AUTH_CHINA_PUBLIC_KEY_URL, OAUTH_CONFIG_URL, X_USER_AGENT

EXPIRES_AT_OFFSET = datetime.timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


@dataclass
class Authentication:
    """Base class for Authentication."""

    username: str
    password: str
    region: Regions
    token: Optional[str] = None
    expires_at: Optional[datetime.datetime] = None

    async def login(self) -> None:
        """Get a valid OAuth token."""
        raise NotImplementedError("Not implemented in Authentication base class.")

    async def get_authentication(self) -> str:
        """Returns a valid Bearer token."""
        if not self.is_token_valid:
            await self.login()
        return f"Bearer {self.token}"

    @property
    def is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if self.token and self.expires_at and datetime.datetime.utcnow() < self.expires_at:
            _LOGGER.debug("Old token is still valid. Not getting a new one.")
            return True
        return False


@dataclass
class MyBMWAuthentication(Authentication):
    """Authentication for MyBMW API."""

    _lock: Optional[asyncio.Lock] = None

    def _create_or_update_lock(self):
        """Makes sure that there is a lock in the current event loop."""
        if not self._lock:
            self._lock = asyncio.Lock()

    async def login(self) -> None:
        """Get a valid OAuth token."""
        self._create_or_update_lock()
        async with self._lock:
            if self.is_token_valid:
                return

            token_data = {}
            if self.region in [Regions.NORTH_AMERICA, Regions.REST_OF_WORLD]:
                token_data = await self._login_row_na()
            elif self.region in [Regions.CHINA]:
                token_data = await self._login_china()

            self.token = token_data["access_token"]
            self.expires_at = token_data["expires_at"] - EXPIRES_AT_OFFSET

    async def _login_row_na(self):  # pylint: disable=too-many-locals
        """Login to Rest of World and North America."""
        try:
            async with httpx.AsyncClient(
                base_url=get_server_url(self.region), headers={"user-agent": "Dart/2.13 (dart:io)"}
            ) as client:
                _LOGGER.debug("Authenticating with MyBMW flow for North America & Rest of World.")

                # Attach raise_for_status event hook
                client.event_hooks["response"].append(raise_for_status_event_handler)

                # Get OAuth2 settings from BMW API
                r_oauth_settings = await client.get(
                    OAUTH_CONFIG_URL,
                    headers={
                        "ocp-apim-subscription-key": get_ocp_apim_key(self.region),
                        "x-user-agent": X_USER_AGENT.format("bmw"),
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

        return {"access_token": response_json["access_token"], "expires_at": expires_at}

    async def _login_china(self):
        try:
            async with httpx.AsyncClient(
                base_url=get_server_url(self.region), headers={"user-agent": "Dart/2.13 (dart:io)"}
            ) as client:
                _LOGGER.debug("Authenticating with MyBMW flow for China.")

                # Attach raise_for_status event hook
                client.event_hooks["response"].append(raise_for_status_event_handler)

                login_header = {"x-user-agent": X_USER_AGENT.format("bmw")}

                # Get current RSA public certificate & use it to encrypt password
                response = await client.get(
                    AUTH_CHINA_PUBLIC_KEY_URL,
                    headers=login_header,
                )
                pem_public_key = response.json()["data"]["value"]

                public_key = RSA.import_key(pem_public_key)
                cipher_rsa = PKCS1_v1_5.new(public_key)
                encrypted = cipher_rsa.encrypt(self.password.encode())
                pw_encrypted = base64.b64encode(encrypted).decode("UTF-8")

                # Get token
                response = await client.post(
                    AUTH_CHINA_LOGIN_URL, headers=login_header, json={"mobile": self.username, "password": pw_encrypted}
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
        }
