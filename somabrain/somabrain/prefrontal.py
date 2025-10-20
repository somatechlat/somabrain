from __future__ import annotations

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .neuromodulators import NeuromodState
import time


@dataclass
class PrefrontalConfig:
    working_memory_capacity: int = 7  # Magical number 7 ± 2
    decision_threshold: float = 0.6
    inhibition_strength: float = 0.8
    planning_depth: int = 3


class PrefrontalCortex:
    """Prefrontal cortex-like component for executive functions."""

    def __init__(self, cfg: PrefrontalConfig):
        self.cfg = cfg
        self.working_memory: List[Dict[str, Any]] = []
        self.active_goals: List[Dict[str, Any]] = []
        self.inhibition_buffer: List[Dict[str, Any]] = []
        self.decision_history: List[Dict[str, Any]] = []

    def maintain_working_memory(self, item: Dict[str, Any]) -> None:
        """Maintain items in working memory with capacity limits."""
        # Add new item
        item['wm_timestamp'] = time.time()
        self.working_memory.append(item)

        # Maintain capacity
        if len(self.working_memory) > self.cfg.working_memory_capacity:
            # Remove oldest items
            self.working_memory.sort(key=lambda x: x.get('wm_timestamp', 0))
            removed = self.working_memory[:-self.cfg.working_memory_capacity]
            self.inhibition_buffer.extend(removed)
            self.working_memory = self.working_memory[-self.cfg.working_memory_capacity:]

    def evaluate_options(self, options: List[Dict[str, Any]],
                        neuromod: NeuromodState) -> List[Dict[str, Any]]:
        """Evaluate decision options considering neuromodulators."""
        evaluated = []

        for option in options:
            # Base evaluation
            value = option.get('value', 0.5)

            # Modulate by neuromodulators
            dopamine_mod = neuromod.dopamine - 0.5  # Center around 0
            serotonin_mod = neuromod.serotonin - 0.5
            noradrenaline_mod = neuromod.noradrenaline

            # Dopamine: reward sensitivity
            value += dopamine_mod * 0.3
            # Serotonin: patience vs impulsivity
            value += serotonin_mod * 0.2
            # Noradrenaline: urgency
            value += noradrenaline_mod * 0.4

            # Consider working memory context
            wm_relevance = self._calculate_wm_relevance(option)
            value += wm_relevance * 0.2

            # Consider inhibition from previous decisions
            inhibition_penalty = self._calculate_inhibition(option)
            value -= inhibition_penalty * self.cfg.inhibition_strength

            option['evaluated_value'] = max(0.0, min(1.0, value))
            evaluated.append(option)

        return evaluated

    def make_decision(self, options: List[Dict[str, Any]],
                     neuromod: NeuromodState) -> Optional[Dict[str, Any]]:
        """Make a decision from evaluated options."""
        if not options:
            return None

        evaluated = self.evaluate_options(options, neuromod)

        # Sort by evaluated value
        evaluated.sort(key=lambda x: x.get('evaluated_value', 0.0), reverse=True)

        best_option = evaluated[0]
        confidence = best_option.get('evaluated_value', 0.0)

        if confidence >= self.cfg.decision_threshold:
            # Record decision for future inhibition
            decision_record = {
                'option': best_option,
                'confidence': confidence,
                'timestamp': time.time(),
                'neuromod_state': neuromod.__dict__.copy()
            }
            self.decision_history.append(decision_record)

            # Maintain recent history
            if len(self.decision_history) > 20:
                self.decision_history = self.decision_history[-20:]

            return best_option

        return None  # No decision above threshold

    def plan_sequence(self, goal: Dict[str, Any], current_state: Dict[str, Any],
                     neuromod: NeuromodState) -> List[Dict[str, Any]]:
        """Generate a sequence of steps to achieve a goal."""
        plan = []
        current = current_state.copy()

        for depth in range(self.cfg.planning_depth):
            # Generate possible actions
            actions = self._generate_actions(current, goal)

            if not actions:
                break

            # Evaluate and select best action
            decision = self.make_decision(actions, neuromod)
            if not decision:
                break

            plan.append(decision)
            # Simulate action outcome
            current = self._simulate_action(current, decision)

            # Check if goal achieved
            if self._goal_achieved(current, goal):
                break

        return plan

    def _calculate_wm_relevance(self, option: Dict[str, Any]) -> float:
        """Calculate relevance to current working memory."""
        if not self.working_memory:
            return 0.0

        relevance = 0.0
        for wm_item in self.working_memory:
            # Simple relevance calculation - could use embeddings
            if any(key in str(option) for key in ['task', 'goal', 'action']):
                if any(key in str(wm_item) for key in ['task', 'goal', 'action']):
                    relevance += 0.2

        return min(1.0, relevance)

    def _calculate_inhibition(self, option: Dict[str, Any]) -> float:
        """Calculate inhibition from similar recent decisions."""
        if not self.decision_history:
            return 0.0

        inhibition = 0.0
        current_time = time.time()

        for decision in self.decision_history[-5:]:  # Last 5 decisions
            age_hours = (current_time - decision.get('timestamp', 0)) / 3600

            # Decay inhibition over time
            decay_factor = max(0.0, 1.0 - age_hours / 24)  # 24 hour decay

            # Check similarity
            if self._options_similar(option, decision.get('option', {})):
                inhibition += decay_factor * 0.3

        return min(1.0, inhibition)

    def _generate_actions(self, state: Dict[str, Any], goal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate possible actions toward goal."""
        actions = []

        # This is a simplified action generation
        # In a real system, this would use more sophisticated planning
        goal_type = goal.get('type', 'generic')

        if goal_type == 'task':
            actions = [
                {'action': 'analyze', 'value': 0.7, 'description': 'Analyze the task requirements'},
                {'action': 'plan', 'value': 0.8, 'description': 'Create a detailed plan'},
                {'action': 'execute', 'value': 0.6, 'description': 'Execute the planned steps'},
                {'action': 'review', 'value': 0.5, 'description': 'Review progress and adjust'}
            ]
        elif goal_type == 'learning':
            actions = [
                {'action': 'study', 'value': 0.8, 'description': 'Study relevant materials'},
                {'action': 'practice', 'value': 0.7, 'description': 'Practice the skill'},
                {'action': 'test', 'value': 0.6, 'description': 'Test understanding'},
                {'action': 'reflect', 'value': 0.5, 'description': 'Reflect on learning'}
            ]

        return actions

    def _simulate_action(self, state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate the outcome of an action."""
        new_state = state.copy()
        action_type = action.get('action', '')

        # Simple state transitions
        if action_type == 'analyze':
            new_state['analyzed'] = True
        elif action_type == 'plan':
            new_state['planned'] = True
        elif action_type == 'execute':
            new_state['executed'] = True
        elif action_type == 'review':
            new_state['reviewed'] = True

        return new_state

    def _goal_achieved(self, state: Dict[str, Any], goal: Dict[str, Any]) -> bool:
        """Check if goal has been achieved."""
        goal_criteria = goal.get('criteria', {})
        for key, value in goal_criteria.items():
            if state.get(key) != value:
                return False
        return True

    def _options_similar(self, option1: Dict[str, Any], option2: Dict[str, Any]) -> bool:
        """Check if two options are similar."""
        keys_to_check = ['action', 'task', 'goal']
        for key in keys_to_check:
            if option1.get(key) == option2.get(key):
                return True
        return False

    def get_working_memory(self) -> List[Dict[str, Any]]:
        """Get current working memory contents."""
        return self.working_memory.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get prefrontal cortex statistics."""
        return {
            'wm_capacity': len(self.working_memory),
            'wm_max_capacity': self.cfg.working_memory_capacity,
            'active_goals': len(self.active_goals),
            'decision_history_length': len(self.decision_history),
            'inhibition_buffer_size': len(self.inhibition_buffer)
        }
