"""
Tests for interactive map functionality in MapTools.

Tests the new get_interactive_map_data() method that generates
JSON for frontend interactive map rendering.
"""

import pytest
import json
from asdrp.actions.geo.map_tools import MapTools


class TestGetInteractiveMapData:
    """Test suite for get_interactive_map_data method."""

    def test_route_map_basic(self):
        """Test basic route map generation."""
        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="San Francisco, CA",
            destination="San Carlos, CA",
            travel_mode="driving"
        )

        # Should return markdown code block with JSON
        assert result.startswith("```json\n")
        assert result.endswith("\n```")

        # Extract and parse JSON
        json_str = result[8:-4]  # Remove ```json\n and \n```
        data = json.loads(json_str)

        # Validate structure
        assert data["type"] == "interactive_map"
        assert data["config"]["map_type"] == "route"
        assert data["config"]["origin"] == "San Francisco, CA"
        assert data["config"]["destination"] == "San Carlos, CA"
        assert data["config"]["travel_mode"] == "DRIVING"
        assert data["config"]["zoom"] == 12

    def test_route_map_with_waypoints(self):
        """Test route map with waypoints."""
        waypoints = ["Palo Alto, CA", "Mountain View, CA"]
        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="San Francisco, CA",
            destination="San Jose, CA",
            waypoints=waypoints,
            travel_mode="bicycling",
            zoom=10
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["config"]["waypoints"] == waypoints
        assert data["config"]["travel_mode"] == "BICYCLING"
        assert data["config"]["zoom"] == 10

    def test_location_map(self):
        """Test location map generation."""
        result = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=37.7749,
            center_lng=-122.4194,
            zoom=14
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["config"]["map_type"] == "location"
        assert data["config"]["center"]["lat"] == 37.7749
        assert data["config"]["center"]["lng"] == -122.4194
        assert data["config"]["zoom"] == 14

    def test_places_map_with_markers(self):
        """Test places map with multiple markers."""
        markers = [
            {"lat": 37.7749, "lng": -122.4194, "title": "City Hall"},
            {"lat": 37.7849, "lng": -122.4094, "title": "Civic Center", "type": "landmark"}
        ]
        result = MapTools.get_interactive_map_data(
            map_type="places",
            center_lat=37.7749,
            center_lng=-122.4194,
            zoom=13,
            markers=markers
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["config"]["map_type"] == "places"
        assert len(data["config"]["markers"]) == 2
        assert data["config"]["markers"][0]["title"] == "City Hall"
        assert data["config"]["markers"][1]["type"] == "landmark"

    def test_route_missing_origin_raises_error(self):
        """Test that route map without origin raises ValueError."""
        with pytest.raises(ValueError, match="Route maps require origin parameter"):
            MapTools.get_interactive_map_data(
                map_type="route",
                destination="San Carlos, CA"
            )

    def test_route_missing_destination_raises_error(self):
        """Test that route map without destination raises ValueError."""
        with pytest.raises(ValueError, match="Route maps require destination parameter"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="San Francisco, CA"
            )

    def test_invalid_map_type_raises_error(self):
        """Test that invalid map_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid map_type"):
            MapTools.get_interactive_map_data(
                map_type="invalid",
                origin="SF",
                destination="SJ"
            )

    def test_invalid_travel_mode_raises_error(self):
        """Test that invalid travel_mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid travel_mode"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                travel_mode="flying"
            )

    def test_invalid_zoom_raises_error(self):
        """Test that zoom outside range raises ValueError."""
        with pytest.raises(ValueError, match="Zoom must be between 1 and 20"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=37.7749,
                center_lng=-122.4194,
                zoom=25
            )

    def test_too_many_waypoints_raises_error(self):
        """Test that >23 waypoints raises ValueError."""
        waypoints = [f"City {i}" for i in range(24)]
        with pytest.raises(ValueError, match="Maximum 23 waypoints"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                waypoints=waypoints
            )

    def test_invalid_center_coordinates_raises_error(self):
        """Test that invalid center coordinates raise ValueError."""
        # Invalid latitude
        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=91.0,
                center_lng=-122.4194
            )

        # Invalid longitude
        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=37.7749,
                center_lng=-181.0
            )

    def test_invalid_marker_coordinates_raises_error(self):
        """Test that invalid marker coordinates raise ValueError."""
        markers = [
            {"lat": 91.0, "lng": -122.4194, "title": "Invalid"}
        ]

        with pytest.raises(ValueError, match="Marker .* latitude must be between"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_marker_missing_required_fields_raises_error(self):
        """Test that markers without lat/lng raise ValueError."""
        markers = [
            {"title": "Missing coordinates"}
        ]

        with pytest.raises(ValueError, match=r"(must have 'lat' and 'lng' fields|must have either \('lat' and 'lng'\) or a non-empty 'address' field)"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_all_travel_modes(self):
        """Test all valid travel modes."""
        modes = ["driving", "walking", "bicycling", "transit"]

        for mode in modes:
            result = MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                travel_mode=mode
            )

            json_str = result[8:-4]
            data = json.loads(json_str)

            assert data["config"]["travel_mode"] == mode.upper()

    def test_json_format_is_valid(self):
        """Test that output is valid JSON wrapped in markdown."""
        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="SF",
            destination="SJ"
        )

        # Check markdown code block format
        assert result.startswith("```json\n")
        assert result.endswith("\n```")

        # Extract JSON and validate it's parseable
        json_str = result[8:-4]
        data = json.loads(json_str)

        # Validate required fields
        assert "type" in data
        assert "config" in data
        assert data["type"] == "interactive_map"

    def test_markers_validation_and_normalization(self):
        """Test that markers are properly validated and normalized."""
        markers = [
            {"lat": 37.7749, "lng": -122.4194, "title": "With title and type", "type": "landmark"},
            {"lat": 37.7849, "lng": -122.4094, "title": "With title only"},
            {"lat": 37.7949, "lng": -122.3994}  # No title or type
        ]

        result = MapTools.get_interactive_map_data(
            map_type="places",
            center_lat=37.7749,
            center_lng=-122.4194,
            markers=markers
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        # All markers should have title and type fields (even if empty)
        for marker in data["config"]["markers"]:
            assert "lat" in marker
            assert "lng" in marker
            assert "title" in marker
            assert "type" in marker

        # Check values
        assert data["config"]["markers"][0]["title"] == "With title and type"
        assert data["config"]["markers"][0]["type"] == "landmark"
        assert data["config"]["markers"][1]["title"] == "With title only"
        assert data["config"]["markers"][1]["type"] == ""
        assert data["config"]["markers"][2]["title"] == ""
        assert data["config"]["markers"][2]["type"] == ""
