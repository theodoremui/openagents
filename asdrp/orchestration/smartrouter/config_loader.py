"""
SmartRouter Configuration Loader

Loads and validates SmartRouter configuration from YAML file.
Uses Pydantic for type-safe configuration with schema validation.

Design Principles:
-----------------
- Single Responsibility: Only responsible for configuration loading
- Type Safety: Pydantic models enforce schema
- Validation: Strict validation with descriptive error messages
- Default Values: Sensible defaults with override capability

Configuration Structure:
-----------------------
config/smartrouter.yaml:
  model:
    interpretation: {...}
    decomposition: {...}
    synthesis: {...}
    evaluation: {...}
  decomposition:
    max_subqueries: 10
    recursion_limit: 3
    fallback_threshold: 0.7
  capabilities:
    agent_id:
      - capability1
      - capability2
  evaluation:
    fallback_message: "I don't have enough information to answer"
    quality_threshold: 0.7
    criteria: [completeness, accuracy, clarity]
  error_handling:
    timeout: 30
    retries: 2
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import yaml

from asdrp.orchestration.smartrouter.exceptions import SmartRouterException


@dataclass
class ModelConfig:
    """
    Configuration for an LLM model.

    Attributes:
        name: Model name (e.g., "gpt-5", "gpt-4.1-mini")
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens in response
    """
    name: str
    temperature: float
    max_tokens: int


@dataclass
class ModelConfigs:
    """
    Model configurations for different SmartRouter operations.

    Attributes:
        interpretation: Model for query interpretation
        decomposition: Model for query decomposition
        synthesis: Model for response synthesis
        evaluation: Model for answer evaluation (LLM Judge)
    """
    interpretation: ModelConfig
    decomposition: ModelConfig
    synthesis: ModelConfig
    evaluation: ModelConfig


@dataclass
class DecompositionConfig:
    """
    Configuration for query decomposition.

    Attributes:
        max_subqueries: Maximum number of subqueries allowed
        recursion_limit: Maximum recursion depth
        fallback_threshold: Threshold for triggering fallback (0.0-1.0)
    """
    max_subqueries: int
    recursion_limit: int
    fallback_threshold: float


@dataclass
class EvaluationConfig:
    """
    Configuration for answer evaluation.

    Attributes:
        fallback_message: Message to return for low-quality answers
        quality_threshold: Minimum quality score (0.0-1.0)
        criteria: List of evaluation criteria
    """
    fallback_message: str
    quality_threshold: float
    criteria: List[str]


@dataclass
class ErrorHandlingConfig:
    """
    Configuration for error handling.

    Attributes:
        timeout: Timeout for agent responses (seconds)
        retries: Number of retries for failed requests
    """
    timeout: float
    retries: int


@dataclass
class SmartRouterConfig:
    """
    Complete SmartRouter configuration.

    Attributes:
        models: Model configurations for different operations
        decomposition: Decomposition settings
        capabilities: Agent capability map
        evaluation: Evaluation settings
        error_handling: Error handling settings
        enabled: Whether SmartRouter is enabled
    """
    models: ModelConfigs
    decomposition: DecompositionConfig
    capabilities: Dict[str, List[str]]
    evaluation: EvaluationConfig
    error_handling: ErrorHandlingConfig
    enabled: bool


class SmartRouterConfigLoader:
    """
    Loader for SmartRouter configuration from YAML.

    Loads configuration from config/smartrouter.yaml with validation,
    merging with defaults from config/open_agents.yaml where appropriate.

    Design follows:
    - Single Responsibility: Only loads and validates config
    - Dependency Injection: Config path can be injected
    - Validation: Strict schema validation with error messages

    Usage:
    ------
    >>> loader = SmartRouterConfigLoader()
    >>> config = loader.load_config()
    >>> print(config.enabled)
    True
    >>> print(config.capabilities["geo"])
    ["geocoding", "reverse_geocoding", "mapping"]
    """

    DEFAULT_CONFIG_PATH = Path("config/smartrouter.yaml")
    AGENTS_CONFIG_PATH = Path("config/open_agents.yaml")

    def __init__(
        self,
        config_path: Optional[Path | str] = None,
        agents_config_path: Optional[Path | str] = None
    ):
        """
        Initialize configuration loader.

        Args:
            config_path: Optional path to smartrouter.yaml (Path or str)
            agents_config_path: Optional path to open_agents.yaml (Path or str)
        """
        # Convert string paths to Path objects
        if config_path is not None and isinstance(config_path, str):
            config_path = Path(config_path)
        if agents_config_path is not None and isinstance(agents_config_path, str):
            agents_config_path = Path(agents_config_path)
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.agents_config_path = agents_config_path or self.AGENTS_CONFIG_PATH
        self._config_cache: Optional[SmartRouterConfig] = None

    def load_config(self, reload: bool = False) -> SmartRouterConfig:
        """
        Load and validate SmartRouter configuration.

        Args:
            reload: If True, force reload from disk (ignore cache)

        Returns:
            SmartRouterConfig with validated settings

        Raises:
            SmartRouterException: If configuration is invalid or missing
        """
        if self._config_cache is not None and not reload:
            return self._config_cache

        try:
            # Load SmartRouter config
            if not self.config_path.exists():
                raise SmartRouterException(
                    f"SmartRouter configuration not found: {self.config_path}",
                    context={"config_path": str(self.config_path)}
                )

            with open(self.config_path, "r") as f:
                config_dict = yaml.safe_load(f)

            if not isinstance(config_dict, dict):
                raise SmartRouterException(
                    "Invalid SmartRouter configuration: root must be a dictionary",
                    context={"config_path": str(self.config_path)}
                )

            # Load agent capabilities from open_agents.yaml if not specified
            if "capabilities" not in config_dict:
                config_dict["capabilities"] = self._load_agent_capabilities()

            # Parse into dataclass
            config = self._parse_config(config_dict)

            # Validate configuration
            self._validate_config(config)

            # Cache and return
            self._config_cache = config
            return config

        except yaml.YAMLError as e:
            raise SmartRouterException(
                f"Failed to parse SmartRouter YAML: {str(e)}",
                context={"config_path": str(self.config_path)},
                original_exception=e
            ) from e
        except Exception as e:
            if isinstance(e, SmartRouterException):
                raise
            raise SmartRouterException(
                f"Failed to load SmartRouter configuration: {str(e)}",
                context={"config_path": str(self.config_path)},
                original_exception=e
            ) from e

    def _load_agent_capabilities(self) -> Dict[str, List[str]]:
        """
        Load agent capabilities from open_agents.yaml.

        Returns:
            Dictionary mapping agent_id to list of capabilities

        Raises:
            SmartRouterException: If agents config cannot be loaded
        """
        try:
            if not self.agents_config_path.exists():
                # Return empty dict if agents config not found
                return {}

            with open(self.agents_config_path, "r") as f:
                agents_config = yaml.safe_load(f)

            if not isinstance(agents_config, dict) or "agents" not in agents_config:
                return {}

            # Extract capabilities from agent configurations
            # For now, use agent type/domain as primary capability
            capabilities = {}
            for agent_id, agent_config in agents_config["agents"].items():
                if not agent_config.get("enabled", True):
                    continue

                # Default: agent_id is its primary capability
                # Can be overridden by explicit "capabilities" field in future
                agent_capabilities = agent_config.get("capabilities", [agent_id])
                if isinstance(agent_capabilities, str):
                    agent_capabilities = [agent_capabilities]

                capabilities[agent_id] = agent_capabilities

            return capabilities

        except Exception as e:
            raise SmartRouterException(
                f"Failed to load agent capabilities: {str(e)}",
                context={"agents_config_path": str(self.agents_config_path)},
                original_exception=e
            ) from e

    def _parse_config(self, config_dict: Dict[str, Any]) -> SmartRouterConfig:
        """
        Parse configuration dictionary into SmartRouterConfig dataclass.

        Args:
            config_dict: Raw configuration dictionary

        Returns:
            SmartRouterConfig instance

        Raises:
            SmartRouterException: If configuration structure is invalid
        """
        try:
            # Parse model configurations
            models_dict = config_dict.get("models", {})
            models = ModelConfigs(
                interpretation=self._parse_model_config(
                    models_dict.get("interpretation", {}),
                    "interpretation"
                ),
                decomposition=self._parse_model_config(
                    models_dict.get("decomposition", {}),
                    "decomposition"
                ),
                synthesis=self._parse_model_config(
                    models_dict.get("synthesis", {}),
                    "synthesis"
                ),
                evaluation=self._parse_model_config(
                    models_dict.get("evaluation", {}),
                    "evaluation"
                ),
            )

            # Parse decomposition config
            decomp_dict = config_dict.get("decomposition", {})
            decomposition = DecompositionConfig(
                max_subqueries=decomp_dict.get("max_subqueries", 10),
                recursion_limit=decomp_dict.get("recursion_limit", 3),
                fallback_threshold=decomp_dict.get("fallback_threshold", 0.7),
            )

            # Parse evaluation config
            eval_dict = config_dict.get("evaluation", {})
            evaluation = EvaluationConfig(
                fallback_message=eval_dict.get(
                    "fallback_message",
                    "I don't have enough information to answer"
                ),
                quality_threshold=eval_dict.get("quality_threshold", 0.7),
                criteria=eval_dict.get("criteria", ["completeness", "accuracy", "clarity"]),
            )

            # Parse error handling config
            error_dict = config_dict.get("error_handling", {})
            error_handling = ErrorHandlingConfig(
                timeout=error_dict.get("timeout", 30.0),
                retries=error_dict.get("retries", 2),
            )

            # Get capabilities
            capabilities = config_dict.get("capabilities", {})

            # Get enabled flag
            enabled = config_dict.get("enabled", True)

            return SmartRouterConfig(
                models=models,
                decomposition=decomposition,
                capabilities=capabilities,
                evaluation=evaluation,
                error_handling=error_handling,
                enabled=enabled,
            )

        except KeyError as e:
            raise SmartRouterException(
                f"Missing required configuration key: {str(e)}",
                context={"config_dict": config_dict}
            ) from e
        except Exception as e:
            raise SmartRouterException(
                f"Failed to parse configuration: {str(e)}",
                context={"config_dict": config_dict},
                original_exception=e
            ) from e

    def _parse_model_config(
        self,
        model_dict: Dict[str, Any],
        config_name: str
    ) -> ModelConfig:
        """
        Parse model configuration dictionary.

        Args:
            model_dict: Model configuration dictionary
            config_name: Name of the config (for error messages)

        Returns:
            ModelConfig instance
        """
        return ModelConfig(
            name=model_dict.get("name", "gpt-4.1-mini"),
            temperature=model_dict.get("temperature", 0.7),
            max_tokens=model_dict.get("max_tokens", 2000),
        )

    def _validate_config(self, config: SmartRouterConfig) -> None:
        """
        Validate configuration values.

        Args:
            config: Configuration to validate

        Raises:
            SmartRouterException: If validation fails
        """
        # Validate decomposition settings
        if config.decomposition.max_subqueries < 1:
            raise SmartRouterException(
                "max_subqueries must be >= 1",
                context={"max_subqueries": config.decomposition.max_subqueries}
            )

        if config.decomposition.recursion_limit < 1:
            raise SmartRouterException(
                "recursion_limit must be >= 1",
                context={"recursion_limit": config.decomposition.recursion_limit}
            )

        if not (0.0 <= config.decomposition.fallback_threshold <= 1.0):
            raise SmartRouterException(
                "fallback_threshold must be between 0.0 and 1.0",
                context={"fallback_threshold": config.decomposition.fallback_threshold}
            )

        # Validate evaluation settings
        if not (0.0 <= config.evaluation.quality_threshold <= 1.0):
            raise SmartRouterException(
                "quality_threshold must be between 0.0 and 1.0",
                context={"quality_threshold": config.evaluation.quality_threshold}
            )

        if not config.evaluation.fallback_message:
            raise SmartRouterException("fallback_message cannot be empty")

        # Validate error handling
        if config.error_handling.timeout <= 0:
            raise SmartRouterException(
                "timeout must be > 0",
                context={"timeout": config.error_handling.timeout}
            )

        if config.error_handling.retries < 0:
            raise SmartRouterException(
                "retries must be >= 0",
                context={"retries": config.error_handling.retries}
            )

        # Validate temperature values
        for model_name, model_config in [
            ("interpretation", config.models.interpretation),
            ("decomposition", config.models.decomposition),
            ("synthesis", config.models.synthesis),
            ("evaluation", config.models.evaluation),
        ]:
            if not (0.0 <= model_config.temperature <= 1.0):
                raise SmartRouterException(
                    f"{model_name} temperature must be between 0.0 and 1.0",
                    context={"model": model_name, "temperature": model_config.temperature}
                )

    def get_capability_map(self) -> Dict[str, List[str]]:
        """
        Get the agent capability map.

        Returns:
            Dictionary mapping agent_id to list of capabilities
        """
        config = self.load_config()
        return config.capabilities

    def is_enabled(self) -> bool:
        """
        Check if SmartRouter is enabled.

        Returns:
            True if enabled, False otherwise
        """
        try:
            config = self.load_config()
            return config.enabled
        except SmartRouterException:
            return False
