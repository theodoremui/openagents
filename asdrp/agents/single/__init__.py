#############################################################################
# single package
#
# Single agent implementations following the AgentProtocol.
#
# This package provides individual agent implementations:
# - GeoAgent: Geocoding and reverse geocoding agent
# - MapAgent: Google Maps-based agent for locations, places, and directions
# - OneAgent: General-purpose agent with web search capabilities
# - YelpAgent: Business and restaurant search agent using Yelp
# - FinanceAgent: Financial data and market information agent
# - ChitchatAgent: Friendly, wholesome social conversation agent
#
#############################################################################

from asdrp.agents.single.geo_agent import (
    create_geo_agent,
    DEFAULT_INSTRUCTIONS as GEO_DEFAULT_INSTRUCTIONS,
)
from asdrp.agents.single.map_agent import (
    create_map_agent,
    DEFAULT_INSTRUCTIONS as MAP_DEFAULT_INSTRUCTIONS,
)
from asdrp.agents.single.one_agent import (
    create_one_agent,
    DEFAULT_INSTRUCTIONS as ONE_DEFAULT_INSTRUCTIONS,
)
from asdrp.agents.single.yelp_agent import (
    create_yelp_agent,
    DEFAULT_INSTRUCTIONS as YELP_DEFAULT_INSTRUCTIONS,
)
from asdrp.agents.single.finance_agent import (
    create_finance_agent,
    DEFAULT_INSTRUCTIONS as FINANCE_DEFAULT_INSTRUCTIONS,
)
from asdrp.agents.single.chitchat_agent import (
    create_chitchat_agent,
    DEFAULT_INSTRUCTIONS as CHITCHAT_DEFAULT_INSTRUCTIONS,
)

__all__ = [
    'create_geo_agent',
    'create_map_agent',
    'create_one_agent',
    'create_yelp_agent',
    'create_finance_agent',
    'create_chitchat_agent',
    'GEO_DEFAULT_INSTRUCTIONS',
    'MAP_DEFAULT_INSTRUCTIONS',
    'ONE_DEFAULT_INSTRUCTIONS',
    'YELP_DEFAULT_INSTRUCTIONS',
    'FINANCE_DEFAULT_INSTRUCTIONS',
    'CHITCHAT_DEFAULT_INSTRUCTIONS',
]

