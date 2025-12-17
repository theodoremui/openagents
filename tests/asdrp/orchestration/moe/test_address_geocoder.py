"""
Tests for AddressGeocoder - venue address extraction and geocoding.

Tests follow SOLID principles:
- Single Responsibility: Each test validates one specific behavior
- Defensive Programming: Tests verify graceful handling of edge cases
- Fail-Safe Design: Geocoder never crashes, always returns partial results
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from asdrp.orchestration.moe.address_geocoder import AddressGeocoder


class TestAddressExtraction:
    """Test venue address extraction from text."""

    def test_extract_numbered_list_with_dashes(self):
        """Test extraction from numbered list format: '1. Name - Address'"""
        geocoder = AddressGeocoder()

        text = """
        1. Souvla - 517 Hayes St, San Francisco, CA 94102
        2. Kokkari Estiatorio - 200 Jackson St, San Francisco, CA 94111
        3. Milos Meze - 3348 Steiner St, San Francisco, CA 94123
        """

        venues = geocoder.extract_venue_addresses(text)

        assert len(venues) == 3
        assert venues[0] == ("Souvla", "517 Hayes St, San Francisco, CA 94102")
        assert venues[1] == ("Kokkari Estiatorio", "200 Jackson St, San Francisco, CA 94111")
        assert venues[2] == ("Milos Meze", "3348 Steiner St, San Francisco, CA 94123")

    def test_extract_unnumbered_list_with_dashes(self):
        """Test extraction without numbers: 'Name - Address'"""
        geocoder = AddressGeocoder()

        text = """
        Souvla - 517 Hayes St, San Francisco, CA 94102
        Kokkari Estiatorio - 200 Jackson St, San Francisco, CA 94111
        """

        venues = geocoder.extract_venue_addresses(text)

        assert len(venues) == 2
        assert venues[0][0] == "Souvla"
        assert venues[1][0] == "Kokkari Estiatorio"

    def test_extract_at_format(self):
        """Test extraction with 'at' keyword: 'Name at Address'"""
        geocoder = AddressGeocoder()

        text = """
        1. Souvla at 517 Hayes St, San Francisco, CA 94102
        2. Kokkari Estiatorio at 200 Jackson St, San Francisco, CA
        """

        venues = geocoder.extract_venue_addresses(text)

        assert len(venues) == 2
        assert venues[0] == ("Souvla", "517 Hayes St, San Francisco, CA 94102")
        assert venues[1] == ("Kokkari Estiatorio", "200 Jackson St, San Francisco, CA")

    def test_extract_colon_format(self):
        """Test extraction with colon format: 'Name: Address'"""
        geocoder = AddressGeocoder()

        text = """
        Souvla: 517 Hayes St, San Francisco, CA 94102
        Kokkari Estiatorio: 200 Jackson St, San Francisco, CA 94111
        """

        venues = geocoder.extract_venue_addresses(text)

        assert len(venues) == 2
        assert "Souvla" in venues[0][0]
        assert "Kokkari" in venues[1][0]

    def test_filter_out_non_addresses(self):
        """Test that lines without street indicators are filtered out."""
        geocoder = AddressGeocoder()

        text = """
        1. Souvla - Rating: 4.5/5
        2. Kokkari Estiatorio - 200 Jackson St, San Francisco, CA
        3. Great Food - Excellent service
        """

        venues = geocoder.extract_venue_addresses(text)

        # Only the one with actual address should be extracted
        assert len(venues) == 1
        assert "Kokkari" in venues[0][0]
        assert "Jackson St" in venues[0][1]

    def test_deduplicate_venues(self):
        """Test that duplicate venue names are deduplicated."""
        geocoder = AddressGeocoder()

        text = """
        1. Souvla - 517 Hayes St, San Francisco, CA 94102
        2. Souvla - 517 Hayes St, San Francisco, CA 94102
        3. Kokkari - 200 Jackson St, San Francisco, CA
        """

        venues = geocoder.extract_venue_addresses(text)

        assert len(venues) == 2  # Souvla deduplicated
        assert venues[0][0] == "Souvla"
        assert venues[1][0] == "Kokkari"

    def test_empty_text_returns_empty_list(self):
        """Test graceful handling of empty text."""
        geocoder = AddressGeocoder()

        assert geocoder.extract_venue_addresses("") == []
        assert geocoder.extract_venue_addresses(None) == []

    def test_no_addresses_returns_empty_list(self):
        """Test graceful handling when no addresses found."""
        geocoder = AddressGeocoder()

        text = "Here are some restaurants: Souvla, Kokkari, Milos Meze"
        venues = geocoder.extract_venue_addresses(text)

        assert venues == []


class TestGeocoding:
    """Test address geocoding functionality."""

    @pytest.mark.asyncio
    async def test_geocode_single_address(self):
        """Test geocoding a single venue address."""
        geocoder = AddressGeocoder()

        venue_addresses = [
            ("Souvla", "517 Hayes St, San Francisco, CA 94102")
        ]

        # Mock GeoTools.get_coordinates_by_address (async)
        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.return_value = {
                "latitude": 37.7769,
                "longitude": -122.4211,
                "formatted_address": "517 Hayes St, San Francisco, CA 94102"
            }

            markers = await geocoder.geocode_addresses(venue_addresses)

            assert len(markers) == 1
            assert markers[0]["lat"] == 37.7769
            assert markers[0]["lng"] == -122.4211
            assert markers[0]["title"] == "Souvla"

    @pytest.mark.asyncio
    async def test_geocode_multiple_addresses(self):
        """Test geocoding multiple venue addresses."""
        geocoder = AddressGeocoder()

        venue_addresses = [
            ("Souvla", "517 Hayes St, San Francisco, CA 94102"),
            ("Kokkari Estiatorio", "200 Jackson St, San Francisco, CA 94111")
        ]

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            # Return different coordinates for each call
            mock_geocode.side_effect = [
                {"latitude": 37.7769, "longitude": -122.4211},
                {"latitude": 37.7955, "longitude": -122.4020}
            ]

            markers = await geocoder.geocode_addresses(venue_addresses)

            assert len(markers) == 2
            assert markers[0]["title"] == "Souvla"
            assert markers[1]["title"] == "Kokkari Estiatorio"

    @pytest.mark.asyncio
    async def test_geocode_skips_failed_addresses(self):
        """Test that geocoding failures are skipped gracefully."""
        geocoder = AddressGeocoder()

        venue_addresses = [
            ("Good Restaurant", "123 Real St, San Francisco, CA"),
            ("Bad Restaurant", "Invalid Address"),
            ("Another Good", "456 Real Ave, San Francisco, CA")
        ]

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            # First and third succeed, second fails
            mock_geocode.side_effect = [
                {"latitude": 37.77, "longitude": -122.42},
                None,  # Geocoding failure
                {"latitude": 37.78, "longitude": -122.43}
            ]

            markers = await geocoder.geocode_addresses(venue_addresses)

            # Should have 2 markers (skipped the failed one)
            assert len(markers) == 2
            assert markers[0]["title"] == "Good Restaurant"
            assert markers[1]["title"] == "Another Good"

    @pytest.mark.asyncio
    async def test_geocode_handles_exception(self):
        """Test that geocoding exceptions don't crash the system."""
        geocoder = AddressGeocoder()

        venue_addresses = [("Test", "Test Address")]

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.side_effect = Exception("API Error")

            markers = await geocoder.geocode_addresses(venue_addresses)

            # Should return empty list, not crash
            assert markers == []

    @pytest.mark.asyncio
    async def test_geocode_respects_max_results(self):
        """Test that max_results parameter limits number of geocoded addresses."""
        geocoder = AddressGeocoder()

        venue_addresses = [
            (f"Restaurant {i}", f"{i} Main St, San Francisco, CA") for i in range(20)
        ]

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.return_value = {"latitude": 37.77, "longitude": -122.42}

            markers = await geocoder.geocode_addresses(venue_addresses, max_results=5)

            # Should only geocode first 5
            assert len(markers) == 5

    @pytest.mark.asyncio
    async def test_geocode_truncates_long_titles(self):
        """Test that long venue names are truncated to 80 characters."""
        geocoder = AddressGeocoder()

        long_name = "A" * 100  # 100 character name
        venue_addresses = [(long_name, "123 Main St, San Francisco, CA")]

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.return_value = {"latitude": 37.77, "longitude": -122.42}

            markers = await geocoder.geocode_addresses(venue_addresses)

            assert len(markers[0]["title"]) == 80


class TestExtractAndGeocode:
    """Test combined extraction + geocoding workflow."""

    @pytest.mark.asyncio
    async def test_extract_and_geocode_full_workflow(self):
        """Test complete workflow from text to geocoded markers."""
        geocoder = AddressGeocoder()

        text = """
        Here are the top 3 Greek restaurants in San Francisco:
        1. Souvla - 517 Hayes St, San Francisco, CA 94102
        2. Kokkari Estiatorio - 200 Jackson St, San Francisco, CA 94111
        3. Milos Meze - 3348 Steiner St, San Francisco, CA 94123
        """

        with patch("asdrp.actions.geo.geo_tools.GeoTools.get_coordinates_by_address", new=AsyncMock()) as mock_geocode:
            mock_geocode.side_effect = [
                {"latitude": 37.7769, "longitude": -122.4211},
                {"latitude": 37.7955, "longitude": -122.4020},
                {"latitude": 37.7684, "longitude": -122.4147}
            ]

            markers = await geocoder.extract_and_geocode(text)

            assert len(markers) == 3
            assert markers[0]["title"] == "Souvla"
            assert markers[1]["title"] == "Kokkari Estiatorio"
            assert markers[2]["title"] == "Milos Meze"
            assert all("lat" in m and "lng" in m for m in markers)

    @pytest.mark.asyncio
    async def test_extract_and_geocode_no_addresses(self):
        """Test graceful handling when no addresses found."""
        geocoder = AddressGeocoder()

        text = "Some text without any addresses"

        markers = await geocoder.extract_and_geocode(text)

        assert markers == []

    @pytest.mark.asyncio
    async def test_extract_and_geocode_geocoding_unavailable(self):
        """Test graceful handling when geocoding is unavailable."""
        geocoder = AddressGeocoder()

        text = "1. Souvla - 517 Hayes St, San Francisco, CA"

        # Mock GeoTools to be unavailable
        with patch.object(geocoder, "_get_geocoding_client", return_value=None):
            markers = await geocoder.extract_and_geocode(text)

            assert markers == []


if __name__ == "__main__":
    # Run with: pytest tests/asdrp/orchestration/moe/test_address_geocoder.py -v
    pytest.main([__file__, "-v"])
