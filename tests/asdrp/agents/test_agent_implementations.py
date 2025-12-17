#############################################################################
# test_agent_implementations.py
#
# Tests for individual agent implementations (geo_agent, yelp_agent, one_agent).
#
# Test Coverage:
# - Agent creation functions (create_geo_agent, create_yelp_agent, create_one_agent)
# - Default instructions
# - Custom instructions
# - Integration with protocol
#
#############################################################################

import pytest
from unittest.mock import patch, AsyncMock

from asdrp.agents.protocol import AgentProtocol, AgentException
from asdrp.agents.single.geo_agent import create_geo_agent, DEFAULT_INSTRUCTIONS as GEO_DEFAULT
from asdrp.agents.single.map_agent import create_map_agent, DEFAULT_INSTRUCTIONS as MAP_DEFAULT
from asdrp.agents.single.yelp_agent import create_yelp_agent, DEFAULT_INSTRUCTIONS as YELP_DEFAULT
from asdrp.agents.single.one_agent import create_one_agent, DEFAULT_INSTRUCTIONS as ONE_DEFAULT
from asdrp.agents.single.finance_agent import create_finance_agent, DEFAULT_INSTRUCTIONS as FINANCE_DEFAULT


class TestGeoAgent:
    """Test GeoAgent implementation."""
    
    def test_create_geo_agent_default_instructions(self):
        """Test GeoAgent creation with default instructions."""
        agent = create_geo_agent()
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == GEO_DEFAULT
        assert isinstance(agent, AgentProtocol)
    
    def test_create_geo_agent_custom_instructions(self):
        """Test GeoAgent creation with custom instructions."""
        custom_instructions = "Custom geocoding instructions"
        agent = create_geo_agent(custom_instructions)
        
        assert agent.name == "GeoAgent"
        assert agent.instructions == custom_instructions
    
    def test_create_geo_agent_none_instructions(self):
        """Test GeoAgent creation with None instructions uses default."""
        agent = create_geo_agent(None)
        
        assert agent.instructions == GEO_DEFAULT
    
    def test_geo_agent_has_tools(self):
        """Test that GeoAgent has tools configured."""
        agent = create_geo_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None


class TestYelpAgent:
    """Test YelpAgent implementation."""
    
    def test_create_yelp_agent_default_instructions(self):
        """Test YelpAgent creation with default instructions."""
        agent = create_yelp_agent()
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == YELP_DEFAULT
        assert isinstance(agent, AgentProtocol)
    
    def test_create_yelp_agent_custom_instructions(self):
        """Test YelpAgent creation with custom instructions."""
        custom_instructions = "Custom Yelp search instructions"
        agent = create_yelp_agent(custom_instructions)
        
        assert agent.name == "YelpAgent"
        assert agent.instructions == custom_instructions
    
    def test_create_yelp_agent_none_instructions(self):
        """Test YelpAgent creation with None instructions uses default."""
        agent = create_yelp_agent(None)
        
        assert agent.instructions == YELP_DEFAULT
    
    def test_yelp_agent_has_tools(self):
        """Test that YelpAgent has tools configured."""
        agent = create_yelp_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None


class TestOneAgent:
    """Test OneAgent implementation."""
    
    def test_create_one_agent_default_instructions(self):
        """Test OneAgent creation with default instructions."""
        agent = create_one_agent()
        
        assert agent.name == "OneAgent"
        assert agent.instructions == ONE_DEFAULT
        assert isinstance(agent, AgentProtocol)
    
    def test_create_one_agent_custom_instructions(self):
        """Test OneAgent creation with custom instructions."""
        custom_instructions = "Custom web search instructions"
        agent = create_one_agent(custom_instructions)
        
        assert agent.name == "OneAgent"
        assert agent.instructions == custom_instructions
    
    def test_create_one_agent_none_instructions(self):
        """Test OneAgent creation with None instructions uses default."""
        agent = create_one_agent(None)
        
        assert agent.instructions == ONE_DEFAULT
    
    def test_one_agent_has_tools(self):
        """Test that OneAgent has tools configured."""
        agent = create_one_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None


class TestMapAgent:
    """Test MapAgent implementation."""
    
    def test_create_map_agent_default_instructions(self):
        """Test MapAgent creation with default instructions."""
        agent = create_map_agent()
        
        assert agent.name == "MapAgent"
        assert agent.instructions == MAP_DEFAULT
        assert isinstance(agent, AgentProtocol)
    
    def test_create_map_agent_custom_instructions(self):
        """Test MapAgent creation with custom instructions."""
        custom_instructions = "Custom mapping instructions"
        agent = create_map_agent(custom_instructions)
        
        assert agent.name == "MapAgent"
        assert agent.instructions == custom_instructions
    
    def test_create_map_agent_none_instructions(self):
        """Test MapAgent creation with None instructions uses default."""
        agent = create_map_agent(None)
        
        assert agent.instructions == MAP_DEFAULT
    
    def test_map_agent_has_tools(self):
        """Test that MapAgent has tools configured."""
        agent = create_map_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None


class TestFinanceAgent:
    """Test FinanceAgent implementation."""
    
    def test_create_finance_agent_default_instructions(self):
        """Test FinanceAgent creation with default instructions."""
        agent = create_finance_agent()
        
        assert agent.name == "FinanceAgent"
        assert agent.instructions == FINANCE_DEFAULT
        assert isinstance(agent, AgentProtocol)
    
    def test_create_finance_agent_custom_instructions(self):
        """Test FinanceAgent creation with custom instructions."""
        custom_instructions = "Custom financial data instructions"
        agent = create_finance_agent(custom_instructions)
        
        assert agent.name == "FinanceAgent"
        assert agent.instructions == custom_instructions
    
    def test_create_finance_agent_none_instructions(self):
        """Test FinanceAgent creation with None instructions uses default."""
        agent = create_finance_agent(None)
        
        assert agent.instructions == FINANCE_DEFAULT
    
    def test_finance_agent_has_tools(self):
        """Test that FinanceAgent has tools configured."""
        agent = create_finance_agent()
        
        assert hasattr(agent, 'tools')
        assert agent.tools is not None


class TestAgentDefaults:
    """Test default instructions for all agents."""
    
    def test_default_instructions_exist(self):
        """Test that all agents have default instructions defined."""
        assert GEO_DEFAULT is not None
        assert MAP_DEFAULT is not None
        assert YELP_DEFAULT is not None
        assert ONE_DEFAULT is not None
        assert FINANCE_DEFAULT is not None
        
        assert isinstance(GEO_DEFAULT, str)
        assert isinstance(MAP_DEFAULT, str)
        assert isinstance(YELP_DEFAULT, str)
        assert isinstance(ONE_DEFAULT, str)
        assert isinstance(FINANCE_DEFAULT, str)
        
        assert len(GEO_DEFAULT) > 0
        assert len(MAP_DEFAULT) > 0
        assert len(YELP_DEFAULT) > 0
        assert len(ONE_DEFAULT) > 0
        assert len(FINANCE_DEFAULT) > 0
    
    def test_default_instructions_are_different(self):
        """Test that default instructions are unique for each agent."""
        assert GEO_DEFAULT != MAP_DEFAULT
        assert GEO_DEFAULT != YELP_DEFAULT
        assert GEO_DEFAULT != ONE_DEFAULT
        assert GEO_DEFAULT != FINANCE_DEFAULT
        assert MAP_DEFAULT != YELP_DEFAULT
        assert MAP_DEFAULT != ONE_DEFAULT
        assert MAP_DEFAULT != FINANCE_DEFAULT
        assert YELP_DEFAULT != ONE_DEFAULT
        assert YELP_DEFAULT != FINANCE_DEFAULT
        assert ONE_DEFAULT != FINANCE_DEFAULT
    
    def test_all_agents_use_defaults_when_none_provided(self):
        """Test that all agents use defaults when None is provided."""
        geo_agent = create_geo_agent(None)
        map_agent = create_map_agent(None)
        yelp_agent = create_yelp_agent(None)
        one_agent = create_one_agent(None)
        finance_agent = create_finance_agent(None)
        
        assert geo_agent.instructions == GEO_DEFAULT
        assert map_agent.instructions == MAP_DEFAULT
        assert yelp_agent.instructions == YELP_DEFAULT
        assert one_agent.instructions == ONE_DEFAULT
        assert finance_agent.instructions == FINANCE_DEFAULT

