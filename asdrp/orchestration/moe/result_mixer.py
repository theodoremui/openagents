"""
Result Mixer - Tier 3 of MoE Pipeline.

Synthesizes expert outputs into coherent response.
"""

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from typing import List, Dict, Any
from dataclasses import dataclass
import os
import re

from asdrp.orchestration.moe.interfaces import IResultMixer
from asdrp.orchestration.moe.config_loader import MoEConfig
from asdrp.orchestration.moe.expert_executor import ExpertResult
from asdrp.orchestration.moe.exceptions import MixingException
from asdrp.orchestration.moe.address_geocoder import AddressGeocoder


@dataclass
class MixedResult:
    """Mixed result from multiple experts."""
    content: str
    weights: Dict[str, float]
    quality_score: float
    metadata: Dict[str, Any] | None = None


class WeightedMixer(IResultMixer):
    """
    Mix expert results using confidence weighting.

    Strategy:
    1. Filter successful results
    2. Weight by expert configuration (from config)
    3. Synthesize using LLM
    """

    def __init__(self, config: MoEConfig):
        """
        Initialize mixer with configuration.

        Args:
            config: MoE configuration
        """
        self._config = config
        self._mixing_strategy = config.moe.get("mixing_strategy", "synthesis")
        self._geocoder = AddressGeocoder()  # Lazy-loaded geocoding for address→coordinate conversion

    async def mix(
        self,
        expert_results: List[ExpertResult],
        expert_ids: List[str],
        query: str
    ) -> MixedResult:
        """
        Mix expert results.

        Args:
            expert_results: Results from experts
            expert_ids: Expert IDs
            query: Original query

        Returns:
            MixedResult with synthesized content

        Raises:
            MixingException: If mixing fails
        """
        try:
            # Filter successful results
            successful = [r for r in expert_results if r.success]

            if not successful:
                return MixedResult(
                    content="I apologize, but I don't have enough information to answer that question accurately.",
                    weights={},
                    quality_score=0.0,
                    metadata={"error": "No successful expert results"}
                )

            # Single expert - no mixing needed, but still apply auto-injection
            if len(successful) == 1:
                result = successful[0]
                content = result.output

                # Apply map auto-injection even for single expert
                # (Yelp alone may return addresses without map)
                content = self._auto_inject_missing_maps(content, query, successful)
                content = await self._auto_inject_map_via_geocoding(content, query, successful)

                return MixedResult(
                    content=content,
                    weights={result.expert_id: 1.0},
                    quality_score=self._estimate_quality(content, successful),
                    metadata=result.metadata
                )

            # Get weights from config
            weights = self._get_weights(successful)

            # Mix using LLM synthesis
            mixed = await self._llm_synthesis(successful, weights, query)

            # Deterministically preserve any interactive visualization blocks produced by experts.
            # Rationale: even with strong prompting, LLM synthesis can omit code blocks; the UI
            # depends on these blocks (e.g., interactive maps) to render rich components.
            mixed.content = self._append_missing_interactive_blocks(
                mixed.content,
                [r.output for r in successful]
            )

            # Defense-in-depth: If this is a route/directions query and no map was generated,
            # try to auto-inject one from route information in the response
            from loguru import logger
            if "```json" not in mixed.content or "interactive_map" not in mixed.content:
                logger.info("[ResultMixer] No interactive map in synthesized response, attempting auto-injection")
                mixed.content = self._auto_inject_missing_maps(mixed.content, query, successful)

                # FINAL FALLBACK: Geocode addresses from response text and inject places map
                # This handles cases where Yelp/other agents return addresses without coordinates
                if "```json" not in mixed.content or "interactive_map" not in mixed.content:
                    logger.info("[ResultMixer] Fallback to geocoding-based map injection")
                    mixed.content = await self._auto_inject_map_via_geocoding(mixed.content, query, successful)
                else:
                    logger.info("[ResultMixer] Map successfully auto-injected from coordinates")
            else:
                logger.info("[ResultMixer] Interactive map already present in synthesized response")

            return mixed

        except Exception as e:
            raise MixingException(f"Result mixing failed: {e}")

    _JSON_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

    def _extract_interactive_json_blocks(self, text: str) -> List[str]:
        """
        Extract interactive visualization JSON code blocks from markdown text.

        We currently target:
        - type == "interactive_map"

        Returns the full markdown block (including the ```json fence) so it can be
        re-inserted verbatim into synthesized output.
        """
        if not text:
            return []

        blocks: List[str] = []
        for m in self._JSON_FENCE_RE.finditer(text):
            raw_json = (m.group(1) or "").strip()
            if not raw_json:
                continue
            try:
                import json

                data = json.loads(raw_json)
                if isinstance(data, dict) and data.get("type") == "interactive_map" and data.get("config"):
                    # Preserve original block text as closely as possible.
                    full_block = f"```json\n{raw_json}\n```"
                    blocks.append(full_block)
            except Exception:
                # Not JSON or not parseable; ignore.
                continue

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: List[str] = []
        for b in blocks:
            if b not in seen:
                seen.add(b)
                deduped.append(b)
        return deduped

    def _auto_inject_missing_maps(
        self,
        synthesized: str,
        query: str,
        expert_results: List[ExpertResult]
    ) -> str:
        """
        Auto-inject interactive maps if missing from route/directions queries.

        This is a defense-in-depth mechanism: if MapAgent was supposed to generate
        a map but didn't, we'll extract route information and create one automatically.

        Args:
            synthesized: The synthesized response text
            query: Original user query
            expert_results: Expert results to extract route info from

        Returns:
            Response with auto-injected map (if applicable)
        """
        # Check if this looks like a route/directions query.
        #
        # IMPORTANT: Do NOT treat generic "map" requests as route queries.
        # Many "show on a map" requests are actually "places" queries (restaurants, businesses),
        # and incorrectly classifying them as routes prevents map injection entirely.
        route_keywords = [
            "direction", "directions", "route", "drive", "travel", "navigate",
            "turn by turn",
        ]
        query_lower = query.lower()
        has_from_to = (" from " in f" {query_lower} ") and (" to " in f" {query_lower} ")
        is_route_query = has_from_to or any(keyword in query_lower for keyword in route_keywords)

        if not is_route_query:
            # Try "places" map injection for restaurant/business map requests.
            return self._auto_inject_missing_places_map(synthesized, query, expert_results)

        # Check if map already exists
        if "```json" in synthesized and "interactive_map" in synthesized:
            return synthesized  # Map already present

        # Try to extract origin/destination from query or response
        import re

        # Pattern 1: "from X to Y"
        match = re.search(r'from\s+([^,]+(?:,\s*[A-Z]{2})?)\s+to\s+([^,]+(?:,\s*[A-Z]{2})?)', query, re.IGNORECASE)
        if match:
            origin = match.group(1).strip()
            destination = match.group(2).strip()
        else:
            # Pattern 2: "X to Y" (without "from")
            match = re.search(r'([A-Za-z\s]+)\s+to\s+([A-Za-z\s]+)', query, re.IGNORECASE)
            if match:
                origin = match.group(1).strip()
                destination = match.group(2).strip()
            else:
                # Can't extract route endpoints; fall back to places-map injection.
                return self._auto_inject_missing_places_map(synthesized, query, expert_results)

        # Generate auto-injected map JSON
        import json
        map_json = {
            "type": "interactive_map",
            "config": {
                "map_type": "route",
                "origin": origin,
                "destination": destination,
                "zoom": 10
            }
        }

        map_block = f"\n\n**Interactive Map** (auto-generated):\n\n```json\n{json.dumps(map_json, indent=2)}\n```\n"

        # Append to response
        return f"{synthesized.rstrip()}\n{map_block}"

    # Enhanced regex patterns for coordinate extraction (more flexible)
    # Matches variations:
    # - **Coordinates**: 37.123, -122.456
    # - Coordinates: 37.123, -122.456
    # - **Location**: 37.123, -122.456
    # - Lat: 37.123, Lng: -122.456
    _COORD_LINE_RE = re.compile(
        r"^\s*(?:-\s*)?(?:\*\*)?(Coordinates|Location|Lat|Position)(?:\*\*)?:\s*([\-0-9.]+)\s*,\s*([\-0-9.]+)\s*$",
        re.IGNORECASE | re.MULTILINE
    )
    # Match both "## Business 1: Name" and "1. **Name**" formats
    _BUSINESS_HEADER_RE = re.compile(
        r"(?:^\s*##\s*Business\s*\d+\s*:\s*(.+?)\s*$|^\s*\d+\.\s*\*\*(.+?)\*\*)",
        re.IGNORECASE | re.MULTILINE
    )

    def _auto_inject_missing_places_map(
        self,
        synthesized: str,
        query: str,
        expert_results: List[ExpertResult]
    ) -> str:
        """
        Auto-inject a "places" interactive map for multi-location business queries.

        This targets queries like:
        - "Show me a detailed map of where the best greek restaurants are in San Francisco."
        - "Show these restaurants on a map"

        We extract coordinates from expert outputs (especially YelpMCPAgent) and
        build a places map JSON block deterministically.
        """
        synthesized = synthesized or ""
        q = (query or "").lower()

        # Only apply when the user asked for a map and we don't already have one.
        if "map" not in q and "maps" not in q:
            return synthesized
        if "```json" in synthesized and "interactive_map" in synthesized:
            return synthesized

        # Require "places-like" intent to avoid injecting maps for unrelated queries that mention "map".
        places_intent = any(w in q for w in ("restaurant", "restaurants", "food", "cafe", "cafes", "bar", "bars", "where"))
        if not places_intent:
            return synthesized

        # Extract (name, lat, lng) markers from expert outputs.
        markers: List[Dict[str, Any]] = []
        from loguru import logger

        for r in expert_results or []:
            text = getattr(r, "output", "") or ""
            if not text:
                continue

            # Enhanced regex returns tuples: (coord_label, lat, lng)
            # We need to extract the coordinate values (groups 2 and 3)
            headers_raw = self._BUSINESS_HEADER_RE.findall(text)
            coords_raw = self._COORD_LINE_RE.findall(text)

            # Extract business names (handles both tuple formats from alternation regex)
            headers = []
            for h in headers_raw:
                if isinstance(h, tuple):
                    # From alternation: ("Name", "") or ("", "Name")
                    name = h[0] or h[1] if len(h) >= 2 else h[0]
                else:
                    name = h
                if name:
                    headers.append(name)

            # Extract coordinates (skip the label group)
            coords = [(lat_s, lng_s) for (_, lat_s, lng_s) in coords_raw]

            logger.debug(f"[ResultMixer] Extracted {len(headers)} business names, {len(coords)} coordinate pairs from expert output")

            if headers and coords and len(headers) == len(coords):
                logger.info(f"[ResultMixer] Found {len(headers)} businesses with coordinates in expert output")
                for name, (lat_s, lng_s) in zip(headers, coords):
                    try:
                        lat = float(lat_s)
                        lng = float(lng_s)
                        markers.append({"lat": lat, "lng": lng, "title": name.strip()[:80]})
                    except Exception as e:
                        logger.warning(f"[ResultMixer] Failed to parse coordinates for '{name}': {e}")
                        continue
            elif headers and coords:
                logger.warning(f"[ResultMixer] Coordinate count mismatch: {len(headers)} businesses, {len(coords)} coordinates")

        # If we couldn't parse YelpMCP-style output, try a generic lat/lng scrape.
        if not markers:
            logger.info("[ResultMixer] No markers from structured format, trying generic coordinate extraction")
            latlng_re = re.compile(r"([\-]?\d{2}\.\d{3,})\s*,\s*([\-]?\d{2,3}\.\d{3,})")
            for r in expert_results or []:
                text = getattr(r, "output", "") or ""
                for lat_s, lng_s in latlng_re.findall(text):
                    try:
                        lat = float(lat_s)
                        lng = float(lng_s)
                        markers.append({"lat": lat, "lng": lng, "title": ""})
                    except Exception:
                        continue
            if markers:
                logger.info(f"[ResultMixer] Generic extraction found {len(markers)} coordinate pairs")

        # Must have at least 1 marker to be useful (single-place queries are common).
        if len(markers) < 1:
            logger.warning(f"[ResultMixer] Insufficient markers ({len(markers)}) for map injection - need at least 1")
            return synthesized

        # Cap markers to avoid enormous payloads.
        markers = markers[:12]

        # Compute map center as average.
        center_lat = sum(m["lat"] for m in markers) / len(markers)
        center_lng = sum(m["lng"] for m in markers) / len(markers)

        try:
            from asdrp.actions.geo.map_tools import MapTools
            map_block = MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=center_lat,
                center_lng=center_lng,
                zoom=15 if len(markers) == 1 else 13,
                markers=markers,
            )
        except Exception:
            return synthesized

        label = "\n\nInteractive map:\n\n"
        return f"{synthesized.rstrip()}{label}{map_block}\n"

    async def _auto_inject_map_via_geocoding(
        self,
        synthesized: str,
        query: str,
        expert_results: List[ExpertResult]
    ) -> str:
        """
        Auto-inject places map by geocoding venue addresses from response text.

        This is the FINAL FALLBACK when:
        1. Query has map intent ("map", "show on map", etc)
        2. No interactive_map JSON exists in response
        3. Coordinate extraction from expert outputs failed (no YelpMCP format)

        Approach:
        - Extract venue addresses from synthesized response text
        - Geocode addresses to coordinates using Google Maps API
        - Generate places map JSON with markers

        Args:
            synthesized: Synthesized response text
            query: Original user query
            expert_results: Expert results (for fallback text extraction)

        Returns:
            Response with auto-injected map (if applicable)

        Example:
            Input: "1. Souvla - 517 Hayes St, San Francisco, CA 94102\\n2. Kokkari..."
            Output: Same text + ```json interactive_map with 2 markers
        """
        synthesized = synthesized or ""
        q = (query or "").lower()

        # Only apply when user asked for a map and we don't already have one
        if "map" not in q and "maps" not in q:
            return synthesized
        if "```json" in synthesized and "interactive_map" in synthesized:
            return synthesized

        # Require "places-like" intent
        places_intent = any(w in q for w in ("restaurant", "restaurants", "food", "cafe", "cafes", "bar", "bars", "shop", "shops", "where"))
        if not places_intent:
            return synthesized

        # Extract venue addresses and geocode them
        try:
            # Try synthesized response first (most reliable)
            markers = await self._geocoder.extract_and_geocode(synthesized, max_markers=12)

            # Fallback: try expert outputs if synthesized had no addresses
            if not markers:
                for r in expert_results or []:
                    text = getattr(r, "output", "") or ""
                    if text:
                        markers = await self._geocoder.extract_and_geocode(text, max_markers=12)
                        if markers:
                            break

            # Single-place queries should still render a map.
            if len(markers) < 1:
                # If geocoding yields nothing, fall back to address-only markers so the frontend
                # can geocode client-side (requires only NEXT_PUBLIC_GOOGLE_MAPS_API_KEY).
                try:
                    venue_addresses = self._geocoder.extract_venue_addresses(synthesized)
                    if venue_addresses:
                        address_markers = [{"address": addr, "title": name[:80]} for name, addr in venue_addresses[:12]]
                        from asdrp.actions.geo.map_tools import MapTools
                        map_block = MapTools.get_interactive_map_data(
                            map_type="places",
                            zoom=15,
                            markers=address_markers,
                        )
                        label = "\n\nInteractive map:\n\n"
                        return f"{synthesized.rstrip()}{label}{map_block}\n"
                except Exception:
                    pass
                return synthesized

            # Generate map JSON
            from asdrp.actions.geo.map_tools import MapTools

            # Calculate center as average of marker positions
            center_lat = sum(m["lat"] for m in markers) / len(markers)
            center_lng = sum(m["lng"] for m in markers) / len(markers)

            map_block = MapTools.get_interactive_map_data(
                map_type="places",
                center_lat=center_lat,
                center_lng=center_lng,
                zoom=15 if len(markers) == 1 else 13,
                markers=markers,
            )

            label = "\n\nInteractive map:\n\n"
            return f"{synthesized.rstrip()}{label}{map_block}\n"

        except Exception as e:
            # Fail safe - never break the response
            from loguru import logger
            logger.warning(f"Geocoding-based map injection failed: {e}")
            return synthesized

    def _append_missing_interactive_blocks(self, synthesized: str, expert_outputs: List[str]) -> str:
        """
        Ensure synthesized response includes interactive visualization blocks from experts.

        If blocks already exist in the synthesized output, do nothing.
        Otherwise append them at the end under a short label.
        """
        synthesized = synthesized or ""
        expert_outputs = expert_outputs or []

        blocks: List[str] = []
        for out in expert_outputs:
            blocks.extend(self._extract_interactive_json_blocks(out))

        if not blocks:
            return synthesized

        missing = [b for b in blocks if b not in synthesized]
        if not missing:
            return synthesized

        suffix = "\n\n".join(missing)
        if synthesized.strip():
            return f"{synthesized.rstrip()}\n\nInteractive map:\n\n{suffix}\n"
        return f"Interactive map:\n\n{suffix}\n"

    def _get_weights(self, results: List[ExpertResult]) -> Dict[str, float]:
        """
        Get weights from config.

        Args:
            results: Expert results

        Returns:
            Dict mapping expert IDs to normalized weights
        """
        weights: Dict[str, float] = {}

        for result in results:
            # Find expert group containing this agent
            for expert_name, expert_config in self._config.experts.items():
                if result.expert_id in expert_config.agents:
                    weights[result.expert_id] = expert_config.weight
                    break

            # Default weight if not found
            if result.expert_id not in weights:
                weights[result.expert_id] = 1.0

        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    async def _llm_synthesis(
        self,
        results: List[ExpertResult],
        weights: Dict[str, float],
        query: str
    ) -> MixedResult:
        """
        Synthesize using LLM.

        Uses gpt-4.1-mini (or configured model) to synthesize expert outputs.

        Args:
            results: Expert results
            weights: Normalized weights
            query: Original query

        Returns:
            MixedResult with synthesized content
        """
        from openai import AsyncOpenAI

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MixingException("OPENAI_API_KEY not set")

        client = AsyncOpenAI(api_key=api_key)
        model_config = self._config.models.get("mixing")

        # Format weighted results
        weighted_results = "\n\n".join([
            f"[Expert: {r.expert_id} - Confidence: {weights.get(r.expert_id, 0.0):.2f}]\n{r.output}"
            for r in results
        ])

        # Get synthesis prompt from config, with fallback to default
        prompt_template = self._config.moe.get("synthesis_prompt")
        if not prompt_template:
            # Fallback to default prompt if not configured
            # NOTE: This produces DETAILED MARKDOWN for the Chat Interface.
            # Voice Mode will separately summarize this output for spoken audio.
            prompt_template = """Synthesize the following expert responses into a comprehensive, well-structured answer.

Expert Responses:
{weighted_results}

Original Query: {query}

OUTPUT FORMAT - DETAILED MARKDOWN FOR CHAT INTERFACE:
Produce a rich, detailed response with proper markdown formatting:

STRUCTURE GUIDELINES:
- Use ## headings for main sections, ### for subsections
- Use **bold** for business names, key terms, and important points
- Use bullet points (-) for listing items, features, or options
- Use numbered lists (1. 2. 3.) for step-by-step instructions or ranked results
- Include all relevant details: ratings, addresses, phone numbers, hours, prices
- Format links as [Text](url) for clickable references

CONTENT REQUIREMENTS:
- Combine ALL relevant information from expert responses
- Weight responses by their confidence scores (higher weight = more reliable)
- Resolve contradictions by favoring higher-weighted experts
- Include specific details: ratings (e.g., "4.5 ⭐"), addresses, contact info
- Maintain factual accuracy - do not invent information
- For coordinates/lat-lng, only include inside json blocks (not in prose)

CRITICAL - PRESERVE INTERACTIVE CONTENT:
- If any expert response contains a ```json code block (especially with "type": "interactive_map"),
  YOU MUST include that EXACT ```json block in your synthesized response
- These JSON blocks are essential for rendering interactive maps, graphs, and visualizations
- DO NOT summarize, paraphrase, or remove ```json blocks - copy them verbatim
- Place the ```json block at the appropriate location in your response (usually at the end)

Synthesized Response:"""

        # Format prompt with template variables
        prompt = prompt_template.format(
            weighted_results=weighted_results,
            query=query
        )

        try:
            response = await client.chat.completions.create(
                model=model_config.name,
                messages=[{"role": "user", "content": prompt}],
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens
            )

            # Defensive: some SDK/error paths can yield an object with choices=None or empty list.
            choices = getattr(response, "choices", None)
            if choices is None:
                raise MixingException("OpenAI synthesis response missing choices (None)")
            if not isinstance(choices, list):
                raise MixingException(f"OpenAI synthesis response choices invalid type: {type(choices)}")
            if len(choices) == 0:
                raise MixingException("OpenAI synthesis response has empty choices list")

            msg = getattr(choices[0], "message", None)
            if msg is None:
                raise MixingException("OpenAI synthesis response message is None")

            content = getattr(msg, "content", None)
            if content is None:
                raise MixingException("OpenAI synthesis response content is None")
            if not isinstance(content, str):
                raise MixingException(f"OpenAI synthesis response content invalid type: {type(content)}")
            if not content.strip():
                raise MixingException("OpenAI synthesis response content is empty")

            # Collect metadata
            metadata = {
                "model": model_config.name,
                "synthesis_tokens": response.usage.total_tokens if response.usage else 0,
                "expert_count": len(results),
            }

            return MixedResult(
                content=content,
                weights=weights,
                quality_score=self._estimate_quality(content, results),
                metadata=metadata
            )

        except Exception as e:
            # Fail open: return the best available expert output instead of raising,
            # so MoE can still provide meaningful results (and not 400).
            try:
                best = None
                best_w = -1.0
                for r in results:
                    w = weights.get(r.expert_id, 0.0)
                    if r.output and w >= best_w:
                        best_w = w
                        best = r.output
                fallback_content = best or (results[0].output if results and results[0].output else "")
            except Exception:
                fallback_content = ""

            return MixedResult(
                content=fallback_content or "I’m having trouble synthesizing results right now, but here’s what I found so far.",
                weights=weights,
                quality_score=self._estimate_quality(fallback_content or "", results),
                metadata={"error": f"synthesis_failed: {e}"},
            )

    def _estimate_quality(self, content: str, results: List[ExpertResult]) -> float:
        """
        Estimate synthesis quality using simple heuristics.

        Args:
            content: Synthesized content
            results: Expert results

        Returns:
            Quality score between 0 and 1
        """
        if not content or not results:
            return 0.0

        # More sources generally means better quality
        source_score = min(len(results) / 3.0, 1.0)

        # Longer, more detailed responses are generally better (to a point)
        word_count = len(content.split())
        length_score = min(word_count / 100.0, 1.0)

        # Weight sources more heavily than length
        return (source_score * 0.7) + (length_score * 0.3)
