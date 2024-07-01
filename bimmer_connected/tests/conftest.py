"""Fixtures for BMW tests."""

from collections import deque
from typing import Deque, Generator, Optional

import pytest
import respx

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.const import Regions
from bimmer_connected.models import AnonymizedResponse

from . import (
    ALL_CHARGING_SETTINGS,
    ALL_PROFILES,
    ALL_STATES,
    TEST_PASSWORD,
    TEST_REGION,
    TEST_USERNAME,
)
from .common import MyBMWMockRouter


@pytest.fixture
def bmw_fixture(request: pytest.FixtureRequest) -> Generator[respx.MockRouter, None, None]:
    """Patch MyBMW login API calls."""
    # Now we can start patching the API calls
    router = MyBMWMockRouter(
        vehicles_to_load=getattr(request, "param", []),
        profiles=ALL_PROFILES,
        states=ALL_STATES,
        charging_settings=ALL_CHARGING_SETTINGS,
    )

    with router:
        yield router


@pytest.fixture
def bmw_log_all_responses(monkeypatch: pytest.MonkeyPatch):
    """Increase the length of the response store to log all responses."""
    temp_store: Deque[AnonymizedResponse] = deque(maxlen=100)
    monkeypatch.setattr("bimmer_connected.api.client.RESPONSE_STORE", temp_store)
    monkeypatch.setattr("bimmer_connected.account.RESPONSE_STORE", temp_store)


@pytest.fixture
def cli_home_dir(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    """Create a temporary home directory for the CLI tests."""
    tmp_path = tmp_path_factory.mktemp("cli-home-")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    return tmp_path


async def prepare_account_with_vehicles(region: Optional[Regions] = None):
    """Initialize account and get vehicles."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, region or TEST_REGION)
    await account.get_vehicles()
    return account
