"""Fixtures for BMW tests."""
from typing import Generator, Optional

try:
    from unittest import mock

    if not hasattr(mock, "AsyncMock"):
        # AsyncMock was only introduced with Python3.8, so we have to use the backported module
        raise ImportError()
except ImportError:
    import mock  # type: ignore[import,no-redef]  # noqa: UP026

import pytest
import respx

from bimmer_connected.account import MyBMWAccount
from bimmer_connected.const import Regions

from . import (
    ALL_CHARGING_SETTINGS,
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
        states=ALL_STATES,
        charging_settings=ALL_CHARGING_SETTINGS,
    )

    with router:
        yield router


async def prepare_account_with_vehicles(region: Optional[Regions] = None, metric: bool = True):
    """Initialize account and get vehicles."""
    account = MyBMWAccount(TEST_USERNAME, TEST_PASSWORD, region or TEST_REGION, use_metric_units=metric)
    await account.get_vehicles()
    return account
