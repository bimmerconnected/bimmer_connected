"""Test the country selection class."""
import unittest

from bimmer_connected.country_selector import valid_regions, Regions, get_region_from_name


class TestCountrySelector(unittest.TestCase):
    """Test the country selection class."""

    def test_valid_regions(self):
        """Test getting list of regions."""
        self.assertIn('china', valid_regions())

    def test_region_from_name(self):
        """Test parsing region from string."""
        self.assertEqual(Regions.CHINA, get_region_from_name('China'))
        self.assertEqual(Regions.REST_OF_WORLD, get_region_from_name('rest_of_world'))
        self.assertEqual(Regions.NORTH_AMERICA, get_region_from_name('nOrTh_AmErica'))

    def test_invalid_region(self):
        """Test exception handling."""
        with self.assertRaises(ValueError):
            get_region_from_name('random_text')
