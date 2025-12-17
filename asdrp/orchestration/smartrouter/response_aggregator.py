"""
ResponseAggregator - Response Collection and Organization

Collects agent responses and organizes them by subquery ID.
Maintains ordering and provides filtering capabilities.

Design Principles:
-----------------
- Single Responsibility: Only responsible for response aggregation
- Simplicity: Straightforward dictionary-based organization
- Robustness: Handles missing/duplicate responses gracefully

Responsibilities:
----------------
- Organize responses by subquery ID
- Maintain execution order
- Filter successful/failed responses
- Provide response statistics
"""

from typing import Dict, List
import logging

from asdrp.orchestration.smartrouter.interfaces import (
    IResponseAggregator,
    AgentResponse,
    Subquery,
)
from asdrp.orchestration.smartrouter.exceptions import SmartRouterException

logger = logging.getLogger(__name__)


class ResponseAggregator(IResponseAggregator):
    """
    Implementation of response aggregation.

    Organizes agent responses into a dictionary keyed by subquery ID.
    Provides filtering and statistics for response analysis.

    Usage:
    ------
    >>> aggregator = ResponseAggregator()
    >>> responses = [response1, response2, response3]
    >>> subqueries = [sq1, sq2, sq3]
    >>> aggregated = aggregator.aggregate(responses, subqueries)
    >>> print(aggregated["sq1"].content)
    The geocoded address is...
    """

    def aggregate(
        self,
        responses: List[AgentResponse],
        subqueries: List[Subquery]
    ) -> Dict[str, AgentResponse]:
        """
        Aggregate responses by subquery ID, maintaining order.

        Creates a dictionary mapping subquery_id to AgentResponse.
        Warns about missing or duplicate responses.

        Args:
            responses: List of agent responses
            subqueries: Original subqueries for context

        Returns:
            Dictionary mapping subquery_id to AgentResponse

        Raises:
            SmartRouterException: If aggregation fails

        Examples:
        ---------
        >>> aggregated = aggregator.aggregate(responses, subqueries)
        >>> assert "sq1" in aggregated
        >>> assert aggregated["sq1"].success
        """
        try:
            logger.debug(
                f"Aggregating {len(responses)} responses for {len(subqueries)} subqueries"
            )

            # Create dictionary from responses
            aggregated: Dict[str, AgentResponse] = {}
            duplicate_count = 0

            for response in responses:
                if response.subquery_id in aggregated:
                    logger.warning(
                        f"Duplicate response for subquery {response.subquery_id}, "
                        f"keeping first response"
                    )
                    duplicate_count += 1
                    continue

                aggregated[response.subquery_id] = response

            # Check for missing responses
            subquery_ids = {sq.id for sq in subqueries}
            missing_ids = subquery_ids - set(aggregated.keys())

            if missing_ids:
                logger.warning(
                    f"Missing responses for {len(missing_ids)} subqueries: {missing_ids}"
                )

            # Log summary
            success_count = sum(1 for r in aggregated.values() if r.success)
            logger.info(
                f"Aggregated {len(aggregated)} responses: "
                f"{success_count} successful, {len(aggregated) - success_count} failed"
            )

            if duplicate_count > 0:
                logger.info(f"Ignored {duplicate_count} duplicate responses")

            return aggregated

        except Exception as e:
            # Safely get counts for context (handle None case)
            response_count = len(responses) if responses is not None else None
            subquery_count = len(subqueries) if subqueries is not None else None
            
            raise SmartRouterException(
                f"Response aggregation failed: {str(e)}",
                context={
                    "response_count": response_count,
                    "subquery_count": subquery_count,
                },
                original_exception=e
            ) from e

    def extract_successful(
        self,
        aggregated: Dict[str, AgentResponse]
    ) -> Dict[str, AgentResponse]:
        """
        Extract only successful responses.

        Filters the aggregated responses to include only those
        where success=True.

        Args:
            aggregated: Aggregated responses

        Returns:
            Dictionary with only successful responses

        Examples:
        ---------
        >>> successful = aggregator.extract_successful(aggregated)
        >>> assert all(r.success for r in successful.values())
        """
        successful = {
            sq_id: response
            for sq_id, response in aggregated.items()
            if response.success
        }

        logger.debug(
            f"Extracted {len(successful)}/{len(aggregated)} successful responses"
        )

        return successful

    def get_failed_responses(
        self,
        aggregated: Dict[str, AgentResponse]
    ) -> Dict[str, AgentResponse]:
        """
        Extract only failed responses.

        Args:
            aggregated: Aggregated responses

        Returns:
            Dictionary with only failed responses
        """
        failed = {
            sq_id: response
            for sq_id, response in aggregated.items()
            if not response.success
        }

        if failed:
            logger.info(
                f"Found {len(failed)} failed responses: "
                f"{list(failed.keys())}"
            )

        return failed

    def get_response_statistics(
        self,
        aggregated: Dict[str, AgentResponse]
    ) -> Dict[str, int]:
        """
        Get statistics about aggregated responses.

        Args:
            aggregated: Aggregated responses

        Returns:
            Dictionary with statistics (total, successful, failed)

        Examples:
        ---------
        >>> stats = aggregator.get_response_statistics(aggregated)
        >>> print(stats)
        {'total': 5, 'successful': 4, 'failed': 1}
        """
        success_count = sum(1 for r in aggregated.values() if r.success)
        failed_count = len(aggregated) - success_count

        return {
            "total": len(aggregated),
            "successful": success_count,
            "failed": failed_count,
        }
