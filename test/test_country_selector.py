"""Test the country selection class."""
import unittest

from bimmer_connected.country_selector import CountrySelector


class TestCountrySelector(unittest.TestCase):
    """Test the country selection class."""

    def test_germany(self):
        """Try getting the url for Germany"""
        cs = CountrySelector()
        self.assertEqual('https://www.bmw-connecteddrive.de', cs.get_url('Germany'))
