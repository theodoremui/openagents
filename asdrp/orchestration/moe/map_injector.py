"""
Map Injector (MoE).

Purpose:
- Guarantee that queries with clear "map intent" result in an `interactive_map` JSON block
  even when MoE falls back (e.g., all experts fail) or when responses come from cache.

Design:
- Deterministic, side-effect free text post-processing
- No dependency on server-side geocoding APIs:
  - Prefer address-only markers so the frontend can geocode using the JS Maps API key
  - Only generate route maps when origin/destination are extractable
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from asdrp.actions.geo.map_tools import MapTools
from asdrp.orchestration.moe.address_geocoder import AddressGeocoder


@dataclass(frozen=True)
class MapIntent:
    kind: str  # "route" | "places" | "unknown"
    origin: Optional[str] = None
    destination: Optional[str] = None


class MapIntentDetector:
    """
    Minimal intent detector:
    - route intent: explicit directions + endpoints ("from X to Y")
    - places intent: user asks for map view / detailed map / show on map, etc.
    """

    _FROM_TO = re.compile(r"\bfrom\s+(.+?)\s+to\s+(.+?)\b", re.IGNORECASE)

    @classmethod
    def detect(cls, query: str) -> Optional[MapIntent]:
        q = (query or "").strip()
        if not q:
            return None

        ql = q.lower()

        # Route intent requires explicit endpoints OR strong direction keywords.
        m = cls._FROM_TO.search(q)
        if m:
            return MapIntent(kind="route", origin=m.group(1).strip(), destination=m.group(2).strip())

        route_markers = ("directions", "route", "turn by turn", "navigate", "driving directions")
        if any(w in ql for w in route_markers):
            # If no endpoints, we can't deterministically build a route map.
            return MapIntent(kind="route", origin=None, destination=None)

        # Places intent (map visualization, not routing).
        places_markers = ("map", "map view", "show on map", "show on a map", "detailed map", "interactive map", "pin")
        if any(w in ql for w in places_markers):
            return MapIntent(kind="places")

        return None


class MapInjector:
    """
    Inject an `interactive_map` JSON block into an answer when appropriate.

    This is intentionally conservative:
    - Only inject when map intent is detected AND the answer doesn't already contain an interactive map.
    - Prefer address-only markers so frontend can geocode and render reliably.
    """

    def __init__(self):
        self._geocoder = AddressGeocoder()

    def inject_if_needed(self, *, query: str, answer: str) -> str:
        text = (answer or "").rstrip()
        if not text:
            return answer or ""

        # Already has an interactive map block.
        if "```json" in text and "interactive_map" in text:
            return text

        intent = MapIntentDetector.detect(query)
        if not intent:
            return text

        # Route: only if we can extract endpoints.
        if intent.kind == "route" and intent.origin and intent.destination:
            try:
                map_block = MapTools.get_interactive_map_data(
                    map_type="route",
                    origin=intent.origin,
                    destination=intent.destination,
                    zoom=10,
                )
                return f"{text}\n\nInteractive map:\n\n{map_block}\n"
            except Exception:
                # Fall through to places injection.
                pass

        # Places: extract venue addresses from the answer text.
        try:
            venues = self._geocoder.extract_venue_addresses(text)
        except Exception:
            venues = []

        if not venues:
            return text

        markers = [{"address": addr, "title": name[:80]} for name, addr in venues[:12] if addr]
        if not markers:
            return text

        try:
            map_block = MapTools.get_interactive_map_data(
                map_type="places",
                zoom=15 if len(markers) == 1 else 13,
                markers=markers,
            )
        except Exception:
            return text

        return f"{text}\n\nInteractive map:\n\n{map_block}\n"


