#!/usr/bin/env python3
"""
Final validation script for MoE Map Rendering Fix.

This script tests the original failing query to ensure the complete fix works:
"Place the top 3 greek restaurants in San Francisco on a detailed map"

Expected behavior:
1. MoE selects appropriate agents (yelp_mcp, yelp, map)
2. YelpMCP agent returns business data (not technical errors)
3. Map agent generates interactive map JSON
4. Result synthesis preserves JSON blocks
5. Response contains both business data and map visualization
"""

import asyncio
import json
import os
import re
import sys
from typing import Dict, Any, List

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("⚠️  Continuing without .env file loading...")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asdrp.orchestration.moe.orchestrator import MoEOrchestrator
from asdrp.agents.agent_factory import AgentFactory


class ValidationResult:
    """Results of validation test."""
    
    def __init__(self):
        self.success = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.details: Dict[str, Any] = {}
    
    def add_error(self, message: str):
        self.success = False
        self.errors.append(message)
        print(f"❌ ERROR: {message}")
    
    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def add_success(self, message: str):
        print(f"✅ SUCCESS: {message}")
    
    def add_detail(self, key: str, value: Any):
        self.details[key] = value


def check_environment_variables() -> ValidationResult:
    """Check required environment variables."""
    result = ValidationResult()
    
    required_vars = [
        "YELP_API_KEY",
        "GOOGLE_API_KEY", 
        "OPENAI_API_KEY"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            result.add_error(f"Missing required environment variable: {var}")
        else:
            result.add_success(f"Environment variable {var} is set")
            # Don't log the actual value for security
            result.add_detail(f"{var}_length", len(value))
    
    return result


def extract_json_blocks(text: str) -> List[Dict[str, Any]]:
    """Extract JSON blocks from text response."""
    json_blocks = []
    
    # Multiple patterns to detect JSON blocks
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{[^`]*"type"\s*:\s*"interactive_map"[^`]*\})\s*```',
        r'(\{[^{}]*"type"\s*:\s*"interactive_map"[^{}]*\})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                if parsed.get("type") == "interactive_map":
                    json_blocks.append(parsed)
            except json.JSONDecodeError:
                continue
    
    return json_blocks


def validate_business_data(response: str) -> ValidationResult:
    """Validate that response contains business data."""
    result = ValidationResult()
    
    # Check for business-related content
    business_indicators = [
        "restaurant", "greek", "san francisco",
        "rating", "address", "phone"
    ]
    
    found_indicators = []
    for indicator in business_indicators:
        if indicator.lower() in response.lower():
            found_indicators.append(indicator)
    
    if len(found_indicators) >= 3:
        result.add_success(f"Business data detected: {found_indicators}")
        result.add_detail("business_indicators", found_indicators)
    else:
        result.add_error(f"Insufficient business data. Found: {found_indicators}")
    
    # Check for technical error messages
    error_indicators = [
        "technical issue", "connection failed", "error occurred",
        "unable to connect", "service unavailable"
    ]
    
    found_errors = []
    for error in error_indicators:
        if error.lower() in response.lower():
            found_errors.append(error)
    
    if found_errors:
        result.add_error(f"Technical errors detected: {found_errors}")
    else:
        result.add_success("No technical error messages found")
    
    return result


def validate_map_data(response: str) -> ValidationResult:
    """Validate that response contains interactive map data."""
    result = ValidationResult()
    
    json_blocks = extract_json_blocks(response)
    
    if not json_blocks:
        result.add_error("No interactive map JSON blocks found")
        return result
    
    result.add_success(f"Found {len(json_blocks)} interactive map JSON block(s)")
    result.add_detail("json_blocks_count", len(json_blocks))
    
    for i, block in enumerate(json_blocks):
        # Validate required fields
        required_fields = ["type", "config"]
        missing_fields = [field for field in required_fields if field not in block]
        
        if missing_fields:
            result.add_error(f"JSON block {i+1} missing fields: {missing_fields}")
            continue
        
        # Validate map configuration
        config = block.get("config", {})
        if "center" not in config:
            result.add_warning(f"JSON block {i+1} missing center coordinates")
        
        if "markers" not in config:
            result.add_error(f"JSON block {i+1} missing markers")
            continue
        
        markers = config.get("markers", [])
        if len(markers) == 0:
            result.add_error(f"JSON block {i+1} has no markers")
        else:
            result.add_success(f"JSON block {i+1} has {len(markers)} markers")
            result.add_detail(f"block_{i+1}_markers", len(markers))
            
            # Validate marker structure
            for j, marker in enumerate(markers):
                if "lat" not in marker or "lng" not in marker:
                    if "address" not in marker:
                        result.add_error(f"Marker {j+1} missing coordinates and address")
                    else:
                        result.add_warning(f"Marker {j+1} has address but no coordinates")
                else:
                    result.add_success(f"Marker {j+1} has valid coordinates")
    
    return result


def validate_agent_selection(trace) -> ValidationResult:
    """Validate that appropriate agents were selected."""
    result = ValidationResult()
    
    if not hasattr(trace, 'selected_experts'):
        result.add_error("No agent selection information available")
        return result
    
    selected_agents = trace.selected_experts
    result.add_detail("selected_agents", selected_agents)
    
    # Check for business agents
    business_agents = [agent for agent in selected_agents if agent in ['yelp', 'yelp_mcp']]
    if not business_agents:
        result.add_error("No business agents selected")
    else:
        result.add_success(f"Business agents selected: {business_agents}")
    
    # Check for map agent
    if 'map' in selected_agents:
        result.add_success("Map agent selected for visualization")
    else:
        result.add_warning("Map agent not selected - may affect visualization")
    
    # Check for appropriate number of agents
    if len(selected_agents) >= 2:
        result.add_success(f"Appropriate number of agents selected: {len(selected_agents)}")
    else:
        result.add_warning(f"Only {len(selected_agents)} agent(s) selected")
    
    return result


def validate_expert_execution(trace) -> ValidationResult:
    """Validate expert execution results."""
    result = ValidationResult()
    
    if not hasattr(trace, 'expert_details'):
        result.add_error("No expert execution details available")
        return result
    
    expert_details = trace.expert_details
    
    successful_experts = [detail for detail in expert_details if detail.status == 'completed']
    failed_experts = [detail for detail in expert_details if detail.status == 'failed']
    
    result.add_detail("successful_experts", len(successful_experts))
    result.add_detail("failed_experts", len(failed_experts))
    
    if len(successful_experts) == 0:
        result.add_error("No experts executed successfully")
        return result
    
    result.add_success(f"{len(successful_experts)} experts executed successfully")
    
    if failed_experts:
        result.add_warning(f"{len(failed_experts)} experts failed")
        for detail in failed_experts:
            if detail.error:
                result.add_warning(f"Expert {detail.expert_id} failed: {detail.error}")
    
    # Check for business agent success
    business_success = any(
        detail.status == 'completed' and detail.expert_id in ['yelp', 'yelp_mcp']
        for detail in expert_details
    )
    
    if business_success:
        result.add_success("At least one business agent executed successfully")
    else:
        result.add_error("No business agents executed successfully")
    
    return result


async def run_validation_query() -> ValidationResult:
    """Run the original failing query and validate results."""
    result = ValidationResult()
    
    try:
        # Initialize MoE orchestrator
        print("🔧 Initializing MoE orchestrator...")
        agent_factory = AgentFactory()
        
        # Load MoE configuration
        from asdrp.orchestration.moe.config_loader import MoEConfigLoader
        from pathlib import Path
        config_loader = MoEConfigLoader(Path("config/moe.yaml"))
        config = config_loader.load_config()
        
        orchestrator = MoEOrchestrator.create_default(
            agent_factory=agent_factory,
            config=config
        )
        
        result.add_success("MoE orchestrator initialized successfully")
        
        # Run the original failing query
        query = "Place the top 3 greek restaurants in San Francisco on a detailed map"
        print(f"🔍 Running query: {query}")
        
        moe_result = await orchestrator.route_query(query)
        
        if not moe_result:
            result.add_error("MoE orchestrator returned no result")
            return result
        
        result.add_success("Query executed successfully")
        result.add_detail("response_length", len(moe_result.response))
        result.add_detail("experts_used", moe_result.experts_used)
        result.add_detail("latency_ms", moe_result.trace.latency_ms if moe_result.trace else None)
        
        # Validate different aspects of the response
        print("\n📊 Validating response components...")
        
        # 1. Validate business data
        business_validation = validate_business_data(moe_result.response)
        if not business_validation.success:
            result.errors.extend(business_validation.errors)
        result.warnings.extend(business_validation.warnings)
        
        # 2. Validate map data
        map_validation = validate_map_data(moe_result.response)
        if not map_validation.success:
            result.errors.extend(map_validation.errors)
        result.warnings.extend(map_validation.warnings)
        
        # 3. Validate agent selection
        if moe_result.trace:
            agent_validation = validate_agent_selection(moe_result.trace)
            if not agent_validation.success:
                result.errors.extend(agent_validation.errors)
            result.warnings.extend(agent_validation.warnings)
            
            # 4. Validate expert execution
            execution_validation = validate_expert_execution(moe_result.trace)
            if not execution_validation.success:
                result.errors.extend(execution_validation.errors)
            result.warnings.extend(execution_validation.warnings)
        
        # Store full response for debugging
        result.add_detail("full_response", moe_result.response)
        
        if result.errors:
            result.success = False
        
    except Exception as e:
        result.add_error(f"Exception during validation: {str(e)}")
        import traceback
        result.add_detail("exception_traceback", traceback.format_exc())
    
    return result


def print_summary(results: List[ValidationResult]):
    """Print validation summary."""
    print("\n" + "="*60)
    print("🎯 FINAL VALIDATION SUMMARY")
    print("="*60)
    
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    
    if total_errors == 0:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ The MoE map rendering fix is working correctly.")
        print("✅ Ready for deployment.")
    else:
        print(f"❌ VALIDATION FAILED: {total_errors} error(s) found")
        print("🔧 Please fix the issues before deployment.")
    
    if total_warnings > 0:
        print(f"⚠️  {total_warnings} warning(s) - review recommended")
    
    print(f"\nDetailed Results:")
    for i, result in enumerate(results):
        test_name = ["Environment Check", "Query Validation"][i] if i < 2 else f"Test {i+1}"
        status = "✅ PASS" if result.success else "❌ FAIL"
        print(f"  {test_name}: {status}")
        
        if result.errors:
            for error in result.errors:
                print(f"    ❌ {error}")
        
        if result.warnings:
            for warning in result.warnings:
                print(f"    ⚠️  {warning}")


async def main():
    """Main validation function."""
    print("🚀 Starting MoE Map Rendering Fix Validation")
    print("="*60)
    
    results = []
    
    # 1. Check environment variables
    print("1️⃣ Checking environment variables...")
    env_result = check_environment_variables()
    results.append(env_result)
    
    if not env_result.success:
        print("❌ Environment validation failed. Cannot proceed with query testing.")
        print_summary(results)
        return 1
    
    # 2. Run validation query
    print("\n2️⃣ Running validation query...")
    query_result = await run_validation_query()
    results.append(query_result)
    
    # Print summary
    print_summary(results)
    
    # Return appropriate exit code
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)