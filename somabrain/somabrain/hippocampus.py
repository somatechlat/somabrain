from __future__ import annotations

from typing import Dict, List, Any
from dataclasses import dataclass
import time
import math


@dataclass
class ConsolidationConfig:
    consolidation_threshold: float = 0.6
    replay_interval_seconds: float = 300  # 5 minutes
    max_replays_per_cycle: int = 10
    decay_rate: float = 0.95


class Hippocampus:
    """Hippocampus-like component for memory consolidation and replay."""

    def __init__(self, cfg: ConsolidationConfig):
        self.cfg = cfg
        self.pending_memories: List[Dict[str, Any]] = []
        self.consolidated_memories: List[Dict[str, Any]] = []
        self.last_replay = time.time()
        self.replay_count = 0

    def add_memory(self, memory: Dict[str, Any]) -> None:
        """Add a memory for potential consolidation."""
        memory['timestamp'] = time.time()
        memory['consolidation_strength'] = 0.0
        self.pending_memories.append(memory)

    def should_consolidate(self, memory: Dict[str, Any]) -> bool:
        """Determine if a memory should be consolidated based on salience and recency."""
        age = time.time() - memory.get('timestamp', 0)
        salience = memory.get('salience', 0.0)

        # Consolidate if salient enough and not too old
        return salience > self.cfg.consolidation_threshold and age < 3600  # 1 hour

    def replay_memories(self) -> List[Dict[str, Any]]:
        """Perform memory replay for consolidation."""
        current_time = time.time()
        if current_time - self.last_replay < self.cfg.replay_interval_seconds:
            return []

        replayed = []
        for memory in self.pending_memories[:self.cfg.max_replays_per_cycle]:
            if self.should_consolidate(memory):
                # Strengthen the memory through replay
                memory['consolidation_strength'] = min(1.0,
                    memory.get('consolidation_strength', 0.0) + 0.1)
                memory['last_replay'] = current_time
                replayed.append(memory.copy())

        # Move consolidated memories to long-term storage
        consolidated = [m for m in self.pending_memories
                       if m.get('consolidation_strength', 0.0) >= 0.8]
        self.consolidated_memories.extend(consolidated)
        self.pending_memories = [m for m in self.pending_memories
                                if m not in consolidated]

        # Decay old pending memories
        self.pending_memories = [m for m in self.pending_memories
                                if time.time() - m.get('timestamp', 0) < 7200]  # 2 hours

        self.last_replay = current_time
        self.replay_count += 1

        return replayed

    def get_consolidated_memories(self, query: str = "", limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve consolidated memories, optionally filtered by query."""
        memories = self.consolidated_memories
        if query:
            # Simple text matching - could be enhanced with embeddings
            memories = [m for m in memories if query.lower() in str(m).lower()]

        # Sort by consolidation strength and recency
        memories.sort(key=lambda m: (m.get('consolidation_strength', 0.0),
                                    m.get('last_replay', 0)), reverse=True)

        return memories[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get hippocampus statistics."""
        return {
            'pending_count': len(self.pending_memories),
            'consolidated_count': len(self.consolidated_memories),
            'replay_count': self.replay_count,
            'avg_consolidation_strength': sum(m.get('consolidation_strength', 0.0)
                                            for m in self.consolidated_memories) / max(1, len(self.consolidated_memories))
        }
