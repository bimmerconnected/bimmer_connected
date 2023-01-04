"""Utils for bimmer_connected.api."""

import base64
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

from bimmer_connected.models import AnonymizedResponse

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


def handle_http_status_error(
    ex: httpx.HTTPStatusError,
    module: str = "MyBMW API",
    log_handler: Optional[logging.Logger] = None,
    debug: bool = False,
) -> None:
    """Try to extract information from response and re-raise Exception."""
    _logger = log_handler or logging.getLogger(__name__)
    _level = logging.DEBUG if debug else logging.ERROR
    try:
        err = ex.response.json()
        _logger.log(_level, "%s error (%s): %s", module, err["error"], err["error_description"])
    except (json.JSONDecodeError, KeyError):
        _logger.log(_level, "%s error: %s", module, ex.response.text)
    if not debug:
        raise ex


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

    url_parts = response.url.path.split("/")[3:]
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
