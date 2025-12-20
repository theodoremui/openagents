"""
Query Accumulation System for Voice Interactions

This module implements intelligent query accumulation that buffers and combines
partial voice inputs into complete queries, addressing the query fragmentation
problem in real-time voice interactions.

Key Features:
- Intelligent text normalization (stutter removal, repetition handling)
- Configurable timeout and buffer limits
- Confidence-based segment filtering
- Rolling buffer for context preservation
- Integration with existing BufferedSTT pipeline

Design Principles:
- SOLID: Single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- DRY: Reusable components with clear abstractions
- YAGNI: Implements only necessary features while maintaining extensibility
- Occam's Razor: Simple solutions favored over complex ones

Architecture:
- IQueryAccumulator: Abstract interface for different accumulation strategies
- BufferedQueryAccumulator: Main implementation with intelligent normalization
- SpeechSegment: Data model for individual speech segments
- AccumulatedQuery: Data model for combined query results
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryStatus(Enum):
    """Status of query accumulation process."""
    ACCUMULATING = "accumulating"  # Still collecting segments
    READY = "ready"               # Query is complete and ready for processing
    TIMEOUT = "timeout"           # Forced completion due to timeout
    ERROR = "error"               # Error occurred during accumulation


@dataclass
class SpeechSegment:
    """
    Individual speech segment from STT processing.
    
    Represents a single chunk of transcribed speech with timing
    and confidence information.
    """
    text: str                    # Transcribed text content
    confidence: float           # STT confidence score (0.0 to 1.0)
    start_time: float          # Segment start time (seconds)
    end_time: float            # Segment end time (seconds)
    silence_after: float       # Duration of silence after segment (seconds)
    
    def __post_init__(self):
        """Validate segment data."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.end_time < self.start_time:
            raise ValueError(f"End time ({self.end_time}) must be >= start time ({self.start_time})")
        if self.silence_after < 0:
            raise ValueError(f"Silence duration must be >= 0, got {self.silence_after}")


@dataclass
class AccumulatedQuery:
    """
    Result of query accumulation process.
    
    Contains the combined text from multiple speech segments
    along with metadata about the accumulation process.
    """
    text: str                           # Combined text from all segments
    segments: List[SpeechSegment]       # Original segments that formed this query
    total_duration: float               # Total duration of all segments (seconds)
    confidence: float                   # Average confidence across segments
    status: QueryStatus                 # Current status of accumulation
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def word_count(self) -> int:
        """Get word count of accumulated text."""
        return len(self.text.split()) if self.text else 0
    
    @property
    def segment_count(self) -> int:
        """Get number of segments in this query."""
        return len(self.segments)


class IQueryAccumulator(ABC):
    """
    Abstract interface for query accumulation strategies.
    
    Enables different approaches to be plugged in:
    - BufferedQueryAccumulator: Intelligent buffering with normalization
    - SimpleQueryAccumulator: Basic concatenation (for testing)
    - MLQueryAccumulator: ML-based accumulation (future enhancement)
    
    This interface follows the Strategy pattern to allow runtime
    selection of accumulation algorithms.
    """

    @abstractmethod
    async def add_segment(self, segment: SpeechSegment) -> AccumulatedQuery:
        """
        Add a speech segment to the accumulator.
        
        Args:
            segment: Speech segment from STT processing
            
        Returns:
            Current accumulated query state
            
        Raises:
            ValueError: If segment is invalid
        """
        pass
    
    @abstractmethod
    async def force_completion(self) -> Optional[AccumulatedQuery]:
        """
        Force completion of current query accumulation.
        
        Returns:
            Final accumulated query if any segments exist, None otherwise
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset accumulator state for new query."""
        pass
    
    @abstractmethod
    def get_current_query(self) -> Optional[AccumulatedQuery]:
        """
        Get current accumulated query without forcing completion.
        
        Returns:
            Current query state or None if no segments
        """
        pass


class BufferedQueryAccumulator(IQueryAccumulator):
    """
    Intelligent query accumulator with text normalization and buffering.
    
    Features:
    - Intelligent text normalization (stutter removal, repetition handling)
    - Configurable timeout and buffer limits
    - Confidence-based segment filtering
    - Rolling buffer for context preservation
    - Word-level deduplication
    - Filler word removal
    
    This implementation addresses common issues in voice transcription:
    1. Stutters and repetitions: "I want I want to find a restaurant"
    2. Filler words: "Um, uh, like, you know"
    3. Low confidence segments: Filters out unreliable transcriptions
    4. Buffer overflow: Prevents infinite accumulation
    5. Context preservation: Maintains recent speech for better understanding
    """
    
    # Common filler words to remove during normalization
    FILLER_WORDS: Set[str] = {
        "um", "uh", "er", "ah", "like", "you know", "i mean", "sort of", 
        "kind of", "basically", "actually", "literally", "well", "so"
    }
    
    # Words that often indicate stuttering when repeated
    STUTTER_PRONE_WORDS: Set[str] = {
        "i", "the", "a", "an", "to", "and", "or", "but", "can", "will", 
        "would", "could", "should", "want", "need", "have", "has"
    }

    def __init__(
        self,
        max_buffer_duration: float = 45.0,
        min_confidence: float = 0.6,
        stutter_threshold: float = 0.3,
        normalization_enabled: bool = True,
        filler_removal_enabled: bool = True,
        deduplication_enabled: bool = True,
        rolling_buffer_size: int = 10
    ):
        """
        Initialize buffered query accumulator.
        
        Args:
            max_buffer_duration: Maximum total duration before forcing completion (seconds)
            min_confidence: Minimum confidence threshold for accepting segments
            stutter_threshold: Time threshold for detecting stutters (seconds)
            normalization_enabled: Enable text normalization features
            filler_removal_enabled: Enable filler word removal
            deduplication_enabled: Enable word-level deduplication
            rolling_buffer_size: Maximum number of segments to keep in rolling buffer
        """
        self._max_duration = max_buffer_duration
        self._min_confidence = min_confidence
        self._stutter_threshold = stutter_threshold
        self._normalization_enabled = normalization_enabled
        self._filler_removal_enabled = filler_removal_enabled
        self._deduplication_enabled = deduplication_enabled
        self._rolling_buffer_size = rolling_buffer_size
        
        # Current accumulation state
        self._segments: List[SpeechSegment] = []
        self._start_time: Optional[float] = None
        self._last_segment_time: Optional[float] = None
        
        # Rolling buffer for context (maintains last N segments)
        self._rolling_buffer: List[SpeechSegment] = []
        
        logger.info(
            f"BufferedQueryAccumulator initialized: "
            f"max_duration={max_buffer_duration}s, min_confidence={min_confidence}, "
            f"normalization={normalization_enabled}"
        )

    async def add_segment(self, segment: SpeechSegment) -> AccumulatedQuery:
        """
        Add speech segment with intelligent normalization and filtering.
        
        Processing Pipeline:
        1. Validate segment
        2. Filter by confidence threshold
        3. Detect and handle stutters
        4. Normalize text (remove fillers, deduplicate)
        5. Check for timeout conditions
        6. Update rolling buffer
        7. Return current accumulated state
        
        Args:
            segment: Speech segment from STT processing
            
        Returns:
            Current accumulated query state
        """
        logger.debug(f"Adding segment: '{segment.text}' (confidence: {segment.confidence:.2f})")
        
        # Initialize timing if this is the first segment
        if self._start_time is None:
            self._start_time = segment.start_time
            logger.debug(f"Started new query accumulation at {self._start_time}")
        
        # Filter low-confidence segments
        if segment.confidence < self._min_confidence:
            logger.debug(
                f"Segment filtered due to low confidence: {segment.confidence:.2f} < {self._min_confidence}"
            )
            return self._build_current_query(QueryStatus.ACCUMULATING)
        
        # Normalize segment if enabled
        if self._normalization_enabled:
            segment = self._normalize_segment(segment)
            
            # Skip empty segments after normalization
            if not segment.text.strip():
                logger.debug("Segment filtered: empty after normalization")
                return self._build_current_query(QueryStatus.ACCUMULATING)
        
        # Add to segments list
        self._segments.append(segment)
        self._last_segment_time = segment.end_time
        
        # Update rolling buffer (maintain fixed size)
        self._rolling_buffer.append(segment)
        if len(self._rolling_buffer) > self._rolling_buffer_size:
            self._rolling_buffer.pop(0)
        
        # Check for timeout condition
        total_duration = segment.end_time - self._start_time
        if total_duration > self._max_duration:
            logger.info(f"Query accumulation timeout: {total_duration:.2f}s > {self._max_duration}s")
            return self._build_current_query(QueryStatus.TIMEOUT)
        
        # Return current state
        return self._build_current_query(QueryStatus.ACCUMULATING)

    async def force_completion(self) -> Optional[AccumulatedQuery]:
        """
        Force completion of current query accumulation.
        
        Returns:
            Final accumulated query if segments exist, None otherwise
        """
        if not self._segments:
            logger.debug("Force completion called but no segments to complete")
            return None
        
        logger.info(f"Forcing completion of query with {len(self._segments)} segments")
        query = self._build_current_query(QueryStatus.READY)
        
        # Reset state after completion
        self.reset()
        
        return query

    def reset(self) -> None:
        """Reset accumulator state for new query."""
        segment_count = len(self._segments)
        self._segments.clear()
        self._start_time = None
        self._last_segment_time = None
        
        # Keep rolling buffer for context across queries
        # Only clear if explicitly requested
        
        if segment_count > 0:
            logger.debug(f"Reset accumulator state ({segment_count} segments cleared)")

    def get_current_query(self) -> Optional[AccumulatedQuery]:
        """
        Get current accumulated query without forcing completion.
        
        Returns:
            Current query state or None if no segments
        """
        if not self._segments:
            return None
        
        return self._build_current_query(QueryStatus.ACCUMULATING)

    def _normalize_segment(self, segment: SpeechSegment) -> SpeechSegment:
        """
        Normalize segment text by removing stutters, fillers, and duplicates.
        
        Normalization Pipeline:
        1. Remove filler words (um, uh, like, etc.)
        2. Detect and remove stutters (repeated words within threshold)
        3. Deduplicate consecutive identical words
        4. Clean up extra whitespace
        
        Args:
            segment: Original speech segment
            
        Returns:
            Normalized speech segment
        """
        original_text = segment.text
        normalized_text = original_text.lower().strip()
        
        if not normalized_text:
            return segment
        
        # Step 1: Remove filler words
        if self._filler_removal_enabled:
            normalized_text = self._remove_filler_words(normalized_text)
        
        # Step 2: Remove stutters
        normalized_text = self._remove_stutters(normalized_text)
        
        # Step 3: Deduplicate consecutive words
        if self._deduplication_enabled:
            normalized_text = self._deduplicate_words(normalized_text)
        
        # Step 4: Clean up whitespace
        normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()
        
        # Log normalization if text changed significantly
        if len(normalized_text) < len(original_text) * 0.8:
            logger.debug(
                f"Significant normalization: '{original_text}' -> '{normalized_text}'"
            )
        
        # Return new segment with normalized text
        return SpeechSegment(
            text=normalized_text,
            confidence=segment.confidence,
            start_time=segment.start_time,
            end_time=segment.end_time,
            silence_after=segment.silence_after
        )

    def _remove_filler_words(self, text: str) -> str:
        """Remove common filler words from text."""
        words = text.split()
        filtered_words = [
            word for word in words 
            if word.lower() not in self.FILLER_WORDS
        ]
        return ' '.join(filtered_words)

    def _remove_stutters(self, text: str) -> str:
        """
        Remove stutters (repeated words that occur within a short time window).
        
        Detects patterns like:
        - "I I want to go"
        - "Can can you help me"
        - "The the restaurant is"
        """
        words = text.split()
        if len(words) < 2:
            return text
        
        filtered_words = []
        i = 0
        
        while i < len(words):
            current_word = words[i].lower()
            
            # Check if this word is repeated immediately after
            if (i + 1 < len(words) and 
                words[i + 1].lower() == current_word and
                current_word in self.STUTTER_PRONE_WORDS):
                
                # Skip the repeated word
                logger.debug(f"Removed stutter: '{current_word}' repeated")
                filtered_words.append(words[i])  # Keep first occurrence
                i += 2  # Skip the duplicate
            else:
                filtered_words.append(words[i])
                i += 1
        
        return ' '.join(filtered_words)

    def _deduplicate_words(self, text: str) -> str:
        """Remove consecutive duplicate words."""
        words = text.split()
        if len(words) < 2:
            return text
        
        deduplicated = [words[0]]
        
        for i in range(1, len(words)):
            if words[i].lower() != words[i-1].lower():
                deduplicated.append(words[i])
            else:
                logger.debug(f"Removed duplicate word: '{words[i]}'")
        
        return ' '.join(deduplicated)

    def _build_current_query(self, status: QueryStatus) -> AccumulatedQuery:
        """
        Build AccumulatedQuery from current segments.
        
        Args:
            status: Current query status
            
        Returns:
            AccumulatedQuery with combined text and metadata
        """
        if not self._segments:
            return AccumulatedQuery(
                text="",
                segments=[],
                total_duration=0.0,
                confidence=0.0,
                status=status,
                metadata={"empty": True}
            )
        
        # Combine text from all segments
        combined_text = ' '.join(segment.text for segment in self._segments if segment.text.strip())
        
        # Calculate total duration
        total_duration = self._last_segment_time - self._start_time if self._start_time else 0.0
        
        # Calculate average confidence
        confidences = [seg.confidence for seg in self._segments]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Build metadata
        metadata = {
            "segment_count": len(self._segments),
            "rolling_buffer_size": len(self._rolling_buffer),
            "normalization_enabled": self._normalization_enabled,
            "start_time": self._start_time,
            "last_segment_time": self._last_segment_time,
            "confidence_range": (min(confidences), max(confidences)) if confidences else (0.0, 0.0)
        }
        
        return AccumulatedQuery(
            text=combined_text,
            segments=self._segments.copy(),  # Copy to prevent external modification
            total_duration=total_duration,
            confidence=avg_confidence,
            status=status,
            metadata=metadata
        )

    def get_rolling_buffer(self) -> List[SpeechSegment]:
        """
        Get copy of rolling buffer for context analysis.
        
        Returns:
            Copy of recent segments for context preservation
        """
        return self._rolling_buffer.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get accumulator statistics for monitoring and debugging.
        
        Returns:
            Dictionary with accumulator statistics
        """
        return {
            "current_segments": len(self._segments),
            "rolling_buffer_size": len(self._rolling_buffer),
            "max_buffer_duration": self._max_duration,
            "min_confidence": self._min_confidence,
            "normalization_enabled": self._normalization_enabled,
            "filler_removal_enabled": self._filler_removal_enabled,
            "deduplication_enabled": self._deduplication_enabled,
            "start_time": self._start_time,
            "last_segment_time": self._last_segment_time,
            "total_duration": (
                self._last_segment_time - self._start_time 
                if self._start_time and self._last_segment_time 
                else 0.0
            )
        }