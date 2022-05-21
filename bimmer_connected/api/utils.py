"""Utils for bimmer_connected.api."""

import base64
import hashlib
import json
import logging
import pathlib
import random
import string
from typing import Dict, List, Union
from uuid import uuid4

import httpx

UNICODE_CHARACTER_SET = string.ascii_letters + string.digits + "-._~"


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
    ex: httpx.HTTPStatusError, module: str = "MyBMW API", log_handler: logging.Logger = None, debug: bool = False
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
        "vin": "some_vin",
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
            else:
                json_data[key] = anonymize_data(value)

    return json_data


def log_to_to_file(content: Union[str, bytes, List, Dict], logfile_path: pathlib.Path, logfile_name: str) -> None:
    """If a log path is set, log all responses to a file."""
    if logfile_path is None or logfile_name is None:
        return

    try:
        parsed_content = json.loads(content)  # type: ignore[arg-type]
        anonymized_data = json.dumps(anonymize_data(parsed_content), indent=2, sort_keys=True)  # type: ignore[arg-type]
        file_extension = "json"
    except json.JSONDecodeError:
        anonymized_data = content.decode("UTF-8") if isinstance(content, bytes) else content  # type: ignore[assignment]
        file_extension = "txt"

    output_path = None
    count = 0

    while output_path is None or output_path.exists():
        output_path = logfile_path / f"{logfile_name}_{count}.{file_extension}"
        count += 1

    with open(output_path, "w", encoding="UTF-8") as logfile:
        logfile.write(anonymized_data)
