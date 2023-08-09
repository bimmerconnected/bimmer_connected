"""Utils for bimmer_connected.api."""

import base64
import datetime
import hashlib
import json
import logging
import mimetypes
import random
import re
import string
from typing import Dict, List, Optional, Union
from uuid import uuid4

import httpx
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad

from bimmer_connected.models import AnonymizedResponse, MyBMWAPIError, MyBMWAuthError, MyBMWQuotaError

UNICODE_CHARACTER_SET = string.ascii_letters + string.digits + "-._~"
RE_VIN = re.compile(r"(?P<vin>WB[a-zA-Z0-9]{15})")
ANONYMIZED_VINS: Dict[str, str] = {}


def generate_token(length: int = 30, chars: str = UNICODE_CHARACTER_SET) -> str:
    """Generate a random token with given length and characters."""
    rand = random.SystemRandom()
    return "".join(rand.choice(chars) for _ in range(length))


def create_s256_code_challenge(code_verifier: str) -> str:
    """Create S256 code_challenge with the given code_verifier."""
    data = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("UTF-8")


def get_correlation_id() -> Dict[str, str]:
    """Generate corrlation headers."""
    correlation_id = str(uuid4())
    return {
        "x-identity-provider": "gcdm",
        "x-correlation-id": correlation_id,
        "bmw-correlation-id": correlation_id,
    }


async def handle_httpstatuserror(
    ex: httpx.HTTPStatusError,
    module: str = "API",
    log_handler: Optional[logging.Logger] = None,
    dont_raise: bool = False,
) -> None:
    """Try to extract information from response and re-raise Exception."""
    _logger = log_handler or logging.getLogger(__name__)
    _level = logging.DEBUG if dont_raise else logging.ERROR

    await ex.response.aread()

    # By default we will raise a MyBMWAPIError
    _ex_to_raise = MyBMWAPIError

    # HTTP status code is 401 or 403, raise MyBMWAuthError instead
    if ex.response.status_code in [401, 403]:
        _ex_to_raise = MyBMWAuthError

    # Quota errors can either be 429 Too Many Requests or 403 Quota Exceeded (instead of 401 Forbidden)
    if ex.response.status_code == 429 or (ex.response.status_code == 403 and "quota" in ex.response.text.lower()):
        _ex_to_raise = MyBMWQuotaError

    try:
        # Try parsing the known BMW API error JSON
        _err = ex.response.json()
        _err_message = f'{type(ex).__name__}: {_err["error"]} - {_err.get("error_description", "")}'
    except (json.JSONDecodeError, KeyError):
        # If format has changed or is not JSON
        _err_message = f"{type(ex).__name__}: {ex.response.text or str(ex)}"

    _logger.log(_level, "%s due to %s", _ex_to_raise.__name__, _err_message)

    if not dont_raise:
        raise _ex_to_raise(_err_message) from ex


def anonymize_data(json_data: Union[List, Dict]) -> Union[List, Dict]:
    """Replace parts of the logfiles containing personal information."""

    replacements = {
        "lat": 12.3456,
        "latitude": 12.3456,
        "lon": 34.5678,
        "longitude": 34.5678,
        "heading": 123,
        "licensePlate": "some_license_plate",
        "name": "some_name",
        "city": "some_city",
        "street": "some_street",
        "streetNumber": "999",
        "postalCode": "some_postal_code",
        "phone": "some_phone",
        "formatted": "some_formatted_address",
        "subtitle": "some_road \u2022 duration \u2022 -- EUR",
    }

    if isinstance(json_data, list):
        json_data = [anonymize_data(v) for v in json_data]
    elif isinstance(json_data, dict):
        for key, value in json_data.items():
            if key in replacements:
                json_data[key] = replacements[key]
            elif isinstance(value, str):
                json_data[key] = RE_VIN.sub(anonymize_vin, json_data[key])
            else:
                json_data[key] = anonymize_data(value)

    return json_data


def anonymize_vin(match: re.Match):
    """Anonymize VINs but keep assignment."""
    vin = match.groupdict()["vin"]
    if vin not in ANONYMIZED_VINS:
        ANONYMIZED_VINS[vin] = f"{vin[:3]}0FINGERPRINT{str(len(ANONYMIZED_VINS)+1).zfill(2)}"
    return ANONYMIZED_VINS[vin]


def anonymize_response(response: httpx.Response) -> AnonymizedResponse:
    """Anonymize a responses URL and content."""
    brand = response.request.headers.get("x-user-agent", ";").split(";")[1]
    brand = f"{brand}-" if brand else ""

    url_parts = response.url.path.split("/")[1:]
    if "bmw-vin" in response.request.headers:
        url_parts.append(response.request.headers["bmw-vin"])
    url_path = RE_VIN.sub(anonymize_vin, "_".join(url_parts))

    try:
        content: Union[List, Dict, str]
        content = anonymize_data(response.json())
    except json.JSONDecodeError:
        content = response.text

    content_type = next(iter((response.headers.get("content-type") or "").split(";")), "")
    file_extension = mimetypes.guess_extension(content_type or ".txt")

    return AnonymizedResponse(f"{brand}{url_path}{file_extension}", content)


def generate_random_base64_string(size: int) -> str:
    """Generate a random base64 string with size."""
    return base64.b64encode(bytes(random.randint(0, 255) for _ in range(size))).decode()[:size]


def generate_cn_nonce(username: str) -> str:
    """Generate a x-login-nonce string."""
    key = generate_random_base64_string(16)
    iv = generate_random_base64_string(16)

    k1 = key[:8]
    i1 = iv[:8]
    k2 = key[8:]
    i2 = iv[8:]

    sha256_hex = SHA256.new((k1 + i1 + "u3.1.0" + k2 + i2).encode()).hexdigest()
    sha256_a = sha256_hex[:32]
    sha256_b = sha256_hex[32:]

    possible_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    random_str = "".join(random.choice(possible_chars) for _ in range(8))

    time_str = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    phone_text = f"{username}&{time_str}&{random_str}"

    cipher_aes = AES.new(key.encode(), AES.MODE_CBC, iv.encode())

    aes_hex = cipher_aes.encrypt(pad(phone_text.encode(), AES.block_size)).hex()

    return k1 + i1 + sha256_a + aes_hex + k2 + i2 + sha256_b
