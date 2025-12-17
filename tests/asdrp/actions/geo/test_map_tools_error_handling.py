"""
Comprehensive error handling tests for map_tools.py.

These tests ensure all MapTools methods handle errors gracefully and
provide clear error messages.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json


class TestMapToolsErrorHandling:
    """Test error handling in MapTools methods."""

    def test_get_interactive_map_data_invalid_map_type(self):
        """Test error when invalid map_type provided."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Invalid map_type"):
            MapTools.get_interactive_map_data(
                map_type="invalid_type",
                origin="SF",
                destination="SJ"
            )

    def test_get_interactive_map_data_invalid_travel_mode(self):
        """Test error when invalid travel_mode provided."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Invalid travel_mode"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                travel_mode="flying"
            )

    def test_get_interactive_map_data_invalid_zoom(self):
        """Test error when zoom out of range."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Zoom must be between 1 and 20"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=37.7749,
                center_lng=-122.4194,
                zoom=25
            )

    def test_get_interactive_map_data_route_missing_origin(self):
        """Test error when route missing origin."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Route maps require origin"):
            MapTools.get_interactive_map_data(
                map_type="route",
                destination="San Carlos, CA"
            )

    def test_get_interactive_map_data_route_missing_destination(self):
        """Test error when route missing destination."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Route maps require destination"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="San Francisco, CA"
            )

    def test_get_interactive_map_data_too_many_waypoints(self):
        """Test error when >23 waypoints provided."""
        from asdrp.actions.geo.map_tools import MapTools

        waypoints = [f"City {i}" for i in range(24)]

        with pytest.raises(ValueError, match="Maximum 23 waypoints"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                waypoints=waypoints
            )

    def test_get_interactive_map_data_invalid_center_lat(self):
        """Test error when center_lat out of range."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=91.0,
                center_lng=-122.4194
            )

    def test_get_interactive_map_data_invalid_center_lng(self):
        """Test error when center_lng out of range."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
            MapTools.get_interactive_map_data(
                map_type="location",
                center_lat=37.7749,
                center_lng=-181.0
            )

    def test_get_interactive_map_data_marker_missing_lat(self):
        """Test error when marker missing lat field."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [{"lng": -122.4194, "title": "Test"}]

        with pytest.raises(ValueError, match=r"(must have 'lat' and 'lng' fields|must have either \('lat' and 'lng'\) or a non-empty 'address' field)"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_get_interactive_map_data_marker_invalid_lat(self):
        """Test error when marker has invalid lat."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [{"lat": 91.0, "lng": -122.4194, "title": "Test"}]

        with pytest.raises(ValueError, match="latitude must be between"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_get_interactive_map_data_marker_invalid_lng(self):
        """Test error when marker has invalid lng."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [{"lat": 37.7749, "lng": -181.0, "title": "Test"}]

        with pytest.raises(ValueError, match="longitude must be between"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_get_interactive_map_data_markers_not_list(self):
        """Test error when markers is not a list."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Markers must be a list"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers="not a list"
            )

    def test_get_interactive_map_data_marker_not_dict(self):
        """Test error when marker is not a dictionary."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = ["not a dict"]

        with pytest.raises(ValueError, match="must be a dictionary"):
            MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=37.7749,
                center_lng=-122.4194,
                markers=markers
            )

    def test_get_interactive_map_data_waypoints_not_list(self):
        """Test error when waypoints is not a list."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Waypoints must be a list"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="SF",
                destination="SJ",
                waypoints="not a list"
            )


class TestMapToolsJSONOutput:
    """Test JSON output format from interactive map data."""

    def test_output_is_valid_json_markdown(self):
        """Test output is valid JSON wrapped in markdown code block."""
        from asdrp.actions.geo.map_tools import MapTools

        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="SF",
            destination="SJ"
        )

        # Should start and end with markdown code block markers
        assert result.startswith("```json\n")
        assert result.endswith("\n```")

        # Extract JSON and validate it's parseable
        json_str = result[8:-4]
        data = json.loads(json_str)

        assert isinstance(data, dict)
        assert "type" in data
        assert "config" in data

    def test_output_json_structure_route(self):
        """Test JSON structure for route maps."""
        from asdrp.actions.geo.map_tools import MapTools

        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="SF",
            destination="SJ",
            travel_mode="driving"
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["type"] == "interactive_map"
        assert data["config"]["map_type"] == "route"
        assert data["config"]["origin"] == "SF"
        assert data["config"]["destination"] == "SJ"
        assert data["config"]["travel_mode"] == "DRIVING"

    def test_output_json_structure_location(self):
        """Test JSON structure for location maps."""
        from asdrp.actions.geo.map_tools import MapTools

        result = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=37.7749,
            center_lng=-122.4194,
            zoom=14
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["type"] == "interactive_map"
        assert data["config"]["map_type"] == "location"
        assert data["config"]["center"]["lat"] == 37.7749
        assert data["config"]["center"]["lng"] == -122.4194
        assert data["config"]["zoom"] == 14

    def test_output_json_structure_places(self):
        """Test JSON structure for places maps."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [
            {"lat": 37.7749, "lng": -122.4194, "title": "City Hall"}
        ]

        result = MapTools.get_interactive_map_data(
            map_type="places",
            center_lat=37.7749,
            center_lng=-122.4194,
            markers=markers
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        assert data["type"] == "interactive_map"
        assert data["config"]["map_type"] == "places"
        assert len(data["config"]["markers"]) == 1
        assert data["config"]["markers"][0]["title"] == "City Hall"

    def test_markers_normalized_with_defaults(self):
        """Test that markers get default title and type fields."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [
            {"lat": 37.7749, "lng": -122.4194},  # No title or type
            {"lat": 37.7849, "lng": -122.4094, "title": "Has title"},  # No type
        ]

        result = MapTools.get_interactive_map_data(
            map_type="places",
            center_lat=37.7749,
            center_lng=-122.4194,
            markers=markers
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        # All markers should have title and type fields
        for marker in data["config"]["markers"]:
            assert "title" in marker
            assert "type" in marker
            assert "lat" in marker
            assert "lng" in marker

        assert data["config"]["markers"][0]["title"] == ""
        assert data["config"]["markers"][0]["type"] == ""
        assert data["config"]["markers"][1]["title"] == "Has title"
        assert data["config"]["markers"][1]["type"] == ""


class TestMapToolsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_origin_string(self):
        """Test handling empty origin string."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Route maps require origin"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="",
                destination="SJ"
            )

    def test_whitespace_only_origin(self):
        """Test handling whitespace-only origin."""
        from asdrp.actions.geo.map_tools import MapTools

        with pytest.raises(ValueError, match="Route maps require origin"):
            MapTools.get_interactive_map_data(
                map_type="route",
                origin="   ",
                destination="SJ"
            )

    def test_zero_waypoints(self):
        """Test handling empty waypoints list."""
        from asdrp.actions.geo.map_tools import MapTools

        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="SF",
            destination="SJ",
            waypoints=[]
        )

        json_str = result[8:-4]
        data = json.loads(json_str)

        # Empty waypoints list should not be included in config
        assert "waypoints" not in data["config"] or data["config"]["waypoints"] == []

    def test_boundary_zoom_values(self):
        """Test zoom at boundary values (1 and 20)."""
        from asdrp.actions.geo.map_tools import MapTools

        # Zoom = 1 (minimum)
        result1 = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=0,
            center_lng=0,
            zoom=1
        )
        json_str1 = result1[8:-4]
        data1 = json.loads(json_str1)
        assert data1["config"]["zoom"] == 1

        # Zoom = 20 (maximum)
        result2 = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=0,
            center_lng=0,
            zoom=20
        )
        json_str2 = result2[8:-4]
        data2 = json.loads(json_str2)
        assert data2["config"]["zoom"] == 20

    def test_boundary_coordinates(self):
        """Test coordinates at boundary values."""
        from asdrp.actions.geo.map_tools import MapTools

        # North pole
        result1 = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=90,
            center_lng=0
        )
        json_str1 = result1[8:-4]
        data1 = json.loads(json_str1)
        assert data1["config"]["center"]["lat"] == 90

        # South pole
        result2 = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=-90,
            center_lng=0
        )
        json_str2 = result2[8:-4]
        data2 = json.loads(json_str2)
        assert data2["config"]["center"]["lat"] == -90

        # International date line
        result3 = MapTools.get_interactive_map_data(
            map_type="location",
            center_lat=0,
            center_lng=180
        )
        json_str3 = result3[8:-4]
        data3 = json.loads(json_str3)
        assert data3["config"]["center"]["lng"] == 180

    def test_all_travel_modes(self):
        """Test all valid travel modes."""
        from asdrp.actions.geo.map_tools import MapTools

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

    def test_unicode_in_location_names(self):
        """Test handling unicode characters in location names."""
        from asdrp.actions.geo.map_tools import MapTools

        result = MapTools.get_interactive_map_data(
            map_type="route",
            origin="São Paulo, Brazil",
            destination="Zürich, Switzerland"
        )

        json_str = result[8:-4]
        data = json.loads(json_str)
        assert data["config"]["origin"] == "São Paulo, Brazil"
        assert data["config"]["destination"] == "Zürich, Switzerland"

    def test_special_characters_in_marker_title(self):
        """Test special characters in marker titles."""
        from asdrp.actions.geo.map_tools import MapTools

        markers = [
            {"lat": 37.7749, "lng": -122.4194, "title": "City & Hall: #1"}
        ]

        result = MapTools.get_interactive_map_data(
            map_type="places",
            center_lat=37.7749,
            center_lng=-122.4194,
            markers=markers
        )

        json_str = result[8:-4]
        data = json.loads(json_str)
        assert data["config"]["markers"][0]["title"] == "City & Hall: #1"
