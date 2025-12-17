"""
Address Geocoder for MoE Result Mixer.

Extracts addresses from text and geocodes them to coordinates for map generation.

Design Principles:
- Single Responsibility: Only handles address extraction and geocoding
- Fail-Safe: Never crashes, always returns partial results on errors
- Defensive: Handles malformed addresses, API failures gracefully
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


class AddressGeocoder:
    """
    Extracts addresses from text and geocodes them to lat/lng coordinates.

    Supports multiple address formats:
    - "Restaurant Name - 123 Main St, City, ST ZIP"
    - "1. Restaurant at 123 Main St, City, ST"
    - "Restaurant Name: 123 Main St, City, State 12345"
    """

    # Pattern: "Name - Address" or "1. Name - Address"
    _NAME_DASH_ADDRESS = re.compile(
        r'^\s*\d*\.?\s*([^-\n]+?)\s*-\s*(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern: "Name at Address"
    _NAME_AT_ADDRESS = re.compile(
        r'^\s*\d*\.?\s*(.+?)\s+at\s+(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern: "Name: Address" (colon format)
    _NAME_COLON_ADDRESS = re.compile(
        r'^\s*\d*\.?\s*([^:\n]+?):\s+(.+?)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern: Just addresses (fallback)
    _STREET_ADDRESS = re.compile(
        r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl),\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}\b',
        re.IGNORECASE
    )

    # Pattern: "Address: 123 Main St, City, ST 12345" (common in LLM responses)
    _ADDRESS_LABEL = re.compile(
        r'^\s*(?:-\s*)?(?:\*\*)?Address(?:\*\*)?\s*:\s*(.+?)\s*$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern: "... location of <NAME>, ..." (common in assistant summaries)
    _LOCATION_OF = re.compile(
        r'location\s+of\s+(.+?)(?:[,\n\.]|$)',
        re.IGNORECASE
    )

    def __init__(self):
        """Initialize geocoder (lazy-load Google Maps client)."""
        self._geocoding_client = None

    def _get_geocoding_client(self):
        """Lazy-load Google Maps Geocoding API client."""
        if self._geocoding_client is None:
            try:
                from asdrp.actions.geo.geo_tools import GeoTools
                self._geocoding_client = GeoTools
            except Exception as e:
                logger.warning(f"Failed to initialize geocoding client: {e}")
                self._geocoding_client = None
        return self._geocoding_client

    def extract_venue_addresses(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract (venue_name, address) pairs from text.

        Args:
            text: Text containing venue listings

        Returns:
            List of (venue_name, address) tuples

        Examples:
            "1. Souvla - 517 Hayes St, San Francisco, CA 94102"
            → [("Souvla", "517 Hayes St, San Francisco, CA 94102")]

            "Kokkari Estiatorio at 200 Jackson St, San Francisco, CA"
            → [("Kokkari Estiatorio", "200 Jackson St, San Francisco, CA")]
        """
        if not text:
            return []

        venues: List[Tuple[str, str]] = []

        # 0) Handle common single-place summaries:
        # "Here is a detailed map showing the location of Milos Meze..."
        # "Address: 3348 Steiner St, San Francisco, CA 94123"
        #
        # We try to pair the first detected name with any Address: lines.
        inferred_name = None
        m = self._LOCATION_OF.search(text)
        if m:
            inferred_name = (m.group(1) or "").strip()

        for m2 in self._ADDRESS_LABEL.finditer(text):
            addr = (m2.group(1) or "").strip()
            if addr:
                venues.append((inferred_name or "Location", addr))

        # Try "Name - Address" pattern first (most common for numbered lists)
        for match in self._NAME_DASH_ADDRESS.finditer(text):
            name = match.group(1).strip()
            address = match.group(2).strip()

            # Filter out lines that don't look like addresses
            if any(word in address.lower() for word in ('street', 'st', 'avenue', 'ave', 'road', 'blvd', 'drive', 'way')):
                venues.append((name, address))

        # Try "Name at Address" pattern if no results yet
        if not venues:
            for match in self._NAME_AT_ADDRESS.finditer(text):
                name = match.group(1).strip()
                address = match.group(2).strip()

                if any(word in address.lower() for word in ('street', 'st', 'avenue', 'ave', 'road', 'blvd', 'drive', 'way')):
                    venues.append((name, address))

        # Try "Name: Address" pattern if still no results
        if not venues:
            for match in self._NAME_COLON_ADDRESS.finditer(text):
                name = match.group(1).strip()
                address = match.group(2).strip()

                if any(word in address.lower() for word in ('street', 'st', 'avenue', 'ave', 'road', 'blvd', 'drive', 'way')):
                    venues.append((name, address))

        # Fallback: extract raw addresses (no explicit venue name)
        if not venues:
            for addr in self._STREET_ADDRESS.findall(text):
                if addr:
                    venues.append(("Location", addr.strip()))

        # Deduplicate while preserving order
        seen_names = set()
        seen_addrs = set()
        unique_venues = []
        for name, addr in venues:
            k_addr = addr.strip().lower()
            if name not in seen_names or k_addr not in seen_addrs:
                unique_venues.append((name, addr))
                seen_names.add(name)
                seen_addrs.add(k_addr)

        return unique_venues

    async def geocode_addresses(
        self,
        venue_addresses: List[Tuple[str, str]],
        max_results: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Geocode list of (venue_name, address) pairs to coordinates.

        Args:
            venue_addresses: List of (venue_name, address) tuples
            max_results: Maximum number of markers to return

        Returns:
            List of marker dicts: [{"lat": float, "lng": float, "title": str}, ...]

        Note:
            - Handles geocoding failures gracefully (skips failed addresses)
            - Returns partial results if some addresses fail
            - Never raises exceptions
        """
        if not venue_addresses:
            return []

        geocoder = self._get_geocoding_client()
        if geocoder is None:
            logger.warning("Geocoding unavailable - skipping coordinate lookup")
            return []

        markers: List[Dict[str, Any]] = []

        for name, address in venue_addresses[:max_results]:
            try:
                # Use GeoTools.get_coordinates_by_address (it's async)
                result = await geocoder.get_coordinates_by_address(address)

                if result and 'latitude' in result and 'longitude' in result:
                    markers.append({
                        "lat": result['latitude'],
                        "lng": result['longitude'],
                        "title": name[:80]  # Truncate long names
                    })
                    logger.debug(f"Geocoded: {name} → ({result['latitude']}, {result['longitude']})")
                else:
                    logger.warning(f"Geocoding returned no coordinates for: {address}")

            except Exception as e:
                logger.warning(f"Failed to geocode '{address}': {e}")
                continue

        return markers

    async def extract_and_geocode(
        self,
        text: str,
        max_markers: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Extract venue addresses from text and geocode them to markers.

        This is the main entry point - combines extraction + geocoding.

        Args:
            text: Text containing venue listings
            max_markers: Maximum number of markers to return

        Returns:
            List of marker dicts ready for map injection

        Example:
            >>> text = "1. Souvla - 517 Hayes St, San Francisco, CA 94102\\n2. Kokkari - 200 Jackson St, SF, CA"
            >>> markers = await geocoder.extract_and_geocode(text)
            >>> len(markers)
            2
            >>> markers[0]["title"]
            "Souvla"
        """
        # Extract venue-address pairs
        venue_addresses = self.extract_venue_addresses(text)

        if not venue_addresses:
            logger.debug("No venue addresses found in text")
            return []

        logger.info(f"Extracted {len(venue_addresses)} venue addresses for geocoding")

        # Geocode to coordinates
        markers = await self.geocode_addresses(venue_addresses, max_results=max_markers)

        logger.info(f"Successfully geocoded {len(markers)}/{len(venue_addresses)} addresses")

        return markers
