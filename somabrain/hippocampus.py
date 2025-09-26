"""
Hippocampus Module for Memory Consolidation.

This module implements a hippocampus-inspired memory consolidation system that manages
the transition of memories from short-term to long-term storage through replay mechanisms.
It provides temporal tagging, salience-based consolidation, and memory replay for
reinforcement learning.

Key Features:
- Memory consolidation based on salience and recency
- Periodic replay cycles for memory strengthening
- Automatic decay of old pending memories
- Consolidation strength tracking
- Query-based retrieval of consolidated memories
- Statistical monitoring of consolidation performance

The hippocampus component works closely with the working memory system to identify
salient memories for consolidation and with the consolidation module for actual
memory strengthening during sleep cycles.

Classes:
    ConsolidationConfig: Configuration parameters for consolidation behavior.
    Hippocampus: Main hippocampus component managing memory consolidation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ConsolidationConfig:
    """
    Configuration parameters for memory consolidation behavior.

    Attributes:
        consolidation_threshold (float): Minimum salience score required for consolidation.
            Memories below this threshold will not be consolidated. Default: 0.6
        replay_interval_seconds (float): Time between replay cycles in seconds.
            Controls how often memory replay occurs. Default: 300 (5 minutes)
        max_replays_per_cycle (int): Maximum memories to replay per cycle.
            Limits computational load during replay. Default: 10
        decay_rate (float): Rate at which old memories decay.
            Not currently used but reserved for future decay implementation. Default: 0.95
    """

    consolidation_threshold: float = 0.6
    replay_interval_seconds: float = 300  # 5 minutes
    max_replays_per_cycle: int = 10
    decay_rate: float = 0.95


class Hippocampus:
    """
    Hippocampus-like component for memory consolidation and replay.

    Manages the consolidation of salient memories from short-term to long-term storage
    through periodic replay cycles. Tracks consolidation strength and provides
    query-based retrieval of consolidated memories.

    Attributes:
        cfg (ConsolidationConfig): Configuration for consolidation behavior.
        pending_memories (List[Dict[str, Any]]): Memories awaiting consolidation.
        consolidated_memories (List[Dict[str, Any]]): Successfully consolidated memories.
        last_replay (float): Timestamp of last replay cycle.
        replay_count (int): Total number of replay cycles performed.
    """

    def __init__(self, cfg: ConsolidationConfig):
        """
        Initialize the hippocampus component.

        Args:
            cfg (ConsolidationConfig): Configuration parameters for consolidation.
        """
        self.cfg = cfg
        self.pending_memories: List[Dict[str, Any]] = []
        self.consolidated_memories: List[Dict[str, Any]] = []
        self.last_replay = time.time()
        self.replay_count = 0

    def add_memory(self, memory: Dict[str, Any]) -> None:
        """
        Add a memory for potential consolidation.

        Adds timestamp and initializes consolidation strength for the memory.
        The memory will be considered for consolidation during the next replay cycle.

        Args:
            memory (Dict[str, Any]): Memory data to add for consolidation.
                Should contain 'salience' key for consolidation decisions.

        Note:
            Memory is added with initial consolidation_strength of 0.0 and current timestamp.
        """
        memory["timestamp"] = time.time()
        memory["consolidation_strength"] = 0.0
        self.pending_memories.append(memory)

    def should_consolidate(self, memory: Dict[str, Any]) -> bool:
        """
        Determine if a memory should be consolidated based on salience and recency.

        Evaluates whether a memory meets the criteria for consolidation by checking
        its salience score against the threshold and ensuring it's not too old.

        Args:
            memory (Dict[str, Any]): Memory to evaluate for consolidation.
                Must contain 'timestamp' and 'salience' keys.

        Returns:
            bool: True if memory should be consolidated, False otherwise.

        Note:
            Memory must have salience > consolidation_threshold and be less than 1 hour old.
        """
        age = time.time() - memory.get("timestamp", 0)
        salience = memory.get("salience", 0.0)

        # Consolidate if salient enough and not too old
        return salience > self.cfg.consolidation_threshold and age < 3600  # 1 hour

    def replay_memories(self) -> List[Dict[str, Any]]:
        """
        Perform memory replay for consolidation.

        Executes a replay cycle if enough time has passed since the last replay.
        Strengthens memories through replay, moves consolidated memories to long-term
        storage, and decays old pending memories.

        Returns:
            List[Dict[str, Any]]: List of memories that were replayed in this cycle.

        Note:
            Only runs if replay_interval_seconds have passed since last replay.
            Limits replay to max_replays_per_cycle memories per cycle.
        """
        current_time = time.time()
        if current_time - self.last_replay < self.cfg.replay_interval_seconds:
            return []

        replayed = []
        for memory in self.pending_memories[: self.cfg.max_replays_per_cycle]:
            if self.should_consolidate(memory):
                # Strengthen the memory through replay
                memory["consolidation_strength"] = min(
                    1.0, memory.get("consolidation_strength", 0.0) + 0.1
                )
                memory["last_replay"] = current_time
                replayed.append(memory.copy())

        # Move consolidated memories to long-term storage
        consolidated = [
            m
            for m in self.pending_memories
            if m.get("consolidation_strength", 0.0) >= 0.8
        ]
        self.consolidated_memories.extend(consolidated)
        self.pending_memories = [
            m for m in self.pending_memories if m not in consolidated
        ]

        # Decay old pending memories
        self.pending_memories = [
            m
            for m in self.pending_memories
            if time.time() - m.get("timestamp", 0) < 7200
        ]  # 2 hours

        self.last_replay = current_time
        self.replay_count += 1

        return replayed

    def get_consolidated_memories(
        self, query: str = "", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve consolidated memories, optionally filtered by query.

        Returns consolidated memories sorted by consolidation strength and recency.
        Supports simple text-based filtering when query is provided.

        Args:
            query (str): Optional text query to filter memories. Default: ""
            limit (int): Maximum number of memories to return. Default: 10

        Returns:
            List[Dict[str, Any]]: List of consolidated memories matching criteria.

        Note:
            Uses simple string matching on memory content. Could be enhanced with
            semantic search using embeddings in the future.
        """
        memories = self.consolidated_memories
        if query:
            # Simple text matching - could be enhanced with embeddings
            memories = [m for m in memories if query.lower() in str(m).lower()]

        # Sort by consolidation strength and recency
        memories.sort(
            key=lambda m: (
                m.get("consolidation_strength", 0.0),
                m.get("last_replay", 0),
            ),
            reverse=True,
        )

        return memories[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get hippocampus statistics.

        Returns comprehensive statistics about the current state of the hippocampus,
        including memory counts, replay performance, and consolidation metrics.

        Returns:
            Dict[str, Any]: Statistics dictionary containing:
                - pending_count: Number of memories awaiting consolidation
                - consolidated_count: Number of successfully consolidated memories
                - replay_count: Total number of replay cycles performed
                - avg_consolidation_strength: Average consolidation strength of consolidated memories
        """
        return {
            "pending_count": len(self.pending_memories),
            "consolidated_count": len(self.consolidated_memories),
            "replay_count": self.replay_count,
            "avg_consolidation_strength": sum(
                m.get("consolidation_strength", 0.0) for m in self.consolidated_memories
            )
            / max(1, len(self.consolidated_memories)),
        }
