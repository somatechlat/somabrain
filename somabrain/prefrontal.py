"""
Prefrontal Cortex Module for Executive Functions.

This module implements prefrontal cortex-inspired executive functions for cognitive control,
decision making, and goal-directed behavior. It manages working memory, evaluates options
considering neuromodulator states, and provides planning capabilities.

Key Features:
- Working memory management with capacity limits
- Neuromodulator-modulated decision evaluation
- Goal-directed planning with configurable depth
- Decision inhibition based on recent history
- Integration with neuromodulator system for cognitive control

Executive Functions:
- Working Memory: Maintains and manages short-term memory items
- Decision Making: Evaluates options with neuromodulator modulation
- Planning: Generates action sequences toward goals
- Inhibition: Prevents repetitive decisions through history tracking
- Goal Management: Tracks active goals and progress

Neuromodulator Integration:
- Dopamine: Influences reward sensitivity in decision making
- Serotonin: Affects patience vs impulsivity balance
- Noradrenaline: Modulates urgency and attention allocation
- Acetylcholine: Supports working memory maintenance

Classes:
    PrefrontalConfig: Configuration parameters for executive functions.
    PrefrontalCortex: Main executive control component.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .neuromodulators import NeuromodState


@dataclass
class PrefrontalConfig:
    """
    Configuration for prefrontal cortex executive functions.

    Defines parameters that control the behavior of executive functions
    including working memory capacity, decision thresholds, and planning depth.

    Attributes:
        working_memory_capacity (int): Maximum items maintained in working memory.
            Based on psychological research suggesting 7±2 items capacity. Default: 7
        decision_threshold (float): Minimum confidence required to make a decision.
            Decisions below this threshold are rejected. Default: 0.6
        inhibition_strength (float): Strength of decision inhibition from history.
            Higher values increase resistance to repeating similar decisions. Default: 0.8
        planning_depth (int): Maximum depth for goal planning sequences.
            Limits computational complexity of planning. Default: 3
    """

    working_memory_capacity: int = 7
    decision_threshold: float = 0.6
    inhibition_strength: float = 0.8
    planning_depth: int = 3


class PrefrontalCortex:
    """
    Prefrontal cortex-like component for executive functions.

    Implements cognitive control mechanisms including working memory management,
    decision making with neuromodulator modulation, goal-directed planning,
    and behavioral inhibition based on decision history.

    Attributes:
        cfg (PrefrontalConfig): Configuration for executive functions.
        working_memory (List[Dict[str, Any]]): Current working memory contents.
        active_goals (List[Dict[str, Any]]): Currently active goals.
        inhibition_buffer (List[Dict[str, Any]]): Inhibited items from working memory.
        decision_history (List[Dict[str, Any]]): History of recent decisions.
    """

    def __init__(self, cfg: PrefrontalConfig):
        """
        Initialize the prefrontal cortex component.

        Args:
            cfg (PrefrontalConfig): Configuration parameters for executive functions.
        """
        self.cfg = cfg
        self.working_memory: List[Dict[str, Any]] = []
        self.active_goals: List[Dict[str, Any]] = []
        self.inhibition_buffer: List[Dict[str, Any]] = []
        self.decision_history: List[Dict[str, Any]] = []

    def maintain_working_memory(self, item: Dict[str, Any]) -> None:
        """
        Maintain items in working memory with capacity limits.

        Adds new items to working memory while enforcing capacity constraints.
        When capacity is exceeded, oldest items are moved to the inhibition buffer.

        Args:
            item (Dict[str, Any]): Item to add to working memory.
                Will be timestamped with current time for LRU management.

        Note:
            Items are sorted by timestamp and excess items are inhibited rather than discarded,
            allowing potential later reactivation.
        """
        # Add new item
        item["wm_timestamp"] = time.time()
        self.working_memory.append(item)

        # Maintain capacity
        if len(self.working_memory) > self.cfg.working_memory_capacity:
            # Remove oldest items
            self.working_memory.sort(key=lambda x: x.get("wm_timestamp", 0))
            removed = self.working_memory[: -self.cfg.working_memory_capacity]
            self.inhibition_buffer.extend(removed)
            self.working_memory = self.working_memory[
                -self.cfg.working_memory_capacity :
            ]

    def evaluate_options(
        self, options: List[Dict[str, Any]], neuromod: NeuromodState
    ) -> List[Dict[str, Any]]:
        """
        Evaluate decision options considering neuromodulator states.

        Modulates option values based on current neuromodulator levels to implement
        context-dependent decision making. Considers working memory relevance and
        applies inhibition from recent decisions.

        Args:
            options (List[Dict[str, Any]]): List of decision options to evaluate.
                Each option should contain a 'value' key with base evaluation.
            neuromod (NeuromodState): Current neuromodulator state for modulation.

        Returns:
            List[Dict[str, Any]]: Options with added 'evaluated_value' field.
                Values are modulated and clamped to [0,1] range.

        Neuromodulator Effects:
            - Dopamine: Increases reward sensitivity (+/- 0.3 modulation)
            - Serotonin: Affects patience vs impulsivity (+/- 0.2 modulation)
            - Noradrenaline: Modulates urgency (+ 0.4 * noradrenaline)
            - Working Memory: Adds relevance bonus (+/- 0.2)
            - Inhibition: Applies penalty based on decision history
        """
        evaluated = []

        for option in options:
            # Base evaluation
            value = option.get("value", 0.5)

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

            option["evaluated_value"] = max(0.0, min(1.0, value))
            evaluated.append(option)

        return evaluated

    def make_decision(
        self, options: List[Dict[str, Any]], neuromod: NeuromodState
    ) -> Optional[Dict[str, Any]]:
        """
        Make a decision from evaluated options.

        Evaluates options, selects the best one above the decision threshold,
        and records the decision for future inhibition learning.

        Args:
            options (List[Dict[str, Any]]): List of decision options.
            neuromod (NeuromodState): Current neuromodulator state.

        Returns:
            Optional[Dict[str, Any]]: Best option if confidence >= threshold, None otherwise.
                Selected option includes 'evaluated_value' field.

        Note:
            Decision history is maintained (max 20 recent decisions) for inhibition learning.
            Only decisions above the confidence threshold are executed.
        """
        if not options:
            return None

        evaluated = self.evaluate_options(options, neuromod)

        # Sort by evaluated value
        evaluated.sort(key=lambda x: x.get("evaluated_value", 0.0), reverse=True)

        best_option = evaluated[0]
        confidence = best_option.get("evaluated_value", 0.0)

        if confidence >= self.cfg.decision_threshold:
            # Record decision for future inhibition
            decision_record = {
                "option": best_option,
                "confidence": confidence,
                "timestamp": time.time(),
                "neuromod_state": neuromod.__dict__.copy(),
            }
            self.decision_history.append(decision_record)

            # Maintain recent history
            if len(self.decision_history) > 20:
                self.decision_history = self.decision_history[-20:]

            return best_option

        return None  # No decision above threshold

    def plan_sequence(
        self,
        goal: Dict[str, Any],
        current_state: Dict[str, Any],
        neuromod: NeuromodState,
    ) -> List[Dict[str, Any]]:
        """
        Generate a sequence of steps to achieve a goal.

        Uses decision making to plan a sequence of actions toward a goal,
        simulating outcomes and checking goal achievement at each step.

        Args:
            goal (Dict[str, Any]): Goal to achieve, containing 'type' and 'criteria'.
            current_state (Dict[str, Any]): Current state representation.
            neuromod (NeuromodState): Current neuromodulator state for decisions.

        Returns:
            List[Dict[str, Any]]: Sequence of planned actions toward the goal.
                Empty list if no valid plan can be generated.

        Planning Process:
            1. Generate possible actions from current state
            2. Evaluate and select best action using decision making
            3. Simulate action outcome
            4. Check if goal achieved
            5. Repeat until goal achieved or max depth reached
        """
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
        """
        Calculate relevance to current working memory.

        Computes how relevant an option is to current working memory contents
        by checking for shared concepts and tasks.

        Args:
            option (Dict[str, Any]): Option to evaluate for relevance.

        Returns:
            float: Relevance score in [0,1] based on working memory overlap.
        """
        if not self.working_memory:
            return 0.0

        relevance = 0.0
        for wm_item in self.working_memory:
            # Simple relevance calculation - could use embeddings
            if any(key in str(option) for key in ["task", "goal", "action"]):
                if any(key in str(wm_item) for key in ["task", "goal", "action"]):
                    relevance += 0.2

        return min(1.0, relevance)

    def _calculate_inhibition(self, option: Dict[str, Any]) -> float:
        """
        Calculate inhibition from similar recent decisions.

        Computes inhibition penalty based on similarity to recent decisions,
        with temporal decay to allow reconsideration over time.

        Args:
            option (Dict[str, Any]): Option to evaluate for inhibition.

        Returns:
            float: Inhibition penalty in [0,1].

        Inhibition Logic:
            - Considers last 5 decisions
            - Applies 24-hour temporal decay
            - Adds 0.3 penalty per similar decision
            - Maximum inhibition of 1.0
        """
        if not self.decision_history:
            return 0.0

        inhibition = 0.0
        current_time = time.time()

        for decision in self.decision_history[-5:]:  # Last 5 decisions
            age_hours = (current_time - decision.get("timestamp", 0)) / 3600

            # Decay inhibition over time
            decay_factor = max(0.0, 1.0 - age_hours / 24)  # 24 hour decay

            # Check similarity
            if self._options_similar(option, decision.get("option", {})):
                inhibition += decay_factor * 0.3

        return min(1.0, inhibition)

    def _generate_actions(
        self, state: Dict[str, Any], goal: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate possible actions toward goal.

        Creates a set of possible actions based on goal type. This is a simplified
        implementation that could be enhanced with more sophisticated planning.

        Args:
            state (Dict[str, Any]): Current state (currently unused).
            goal (Dict[str, Any]): Goal containing 'type' field.

        Returns:
            List[Dict[str, Any]]: List of possible actions with value and description.

        Supported Goal Types:
            - 'task': Analyze, plan, execute, review actions
            - 'learning': Study, practice, test, reflect actions
        """
        actions = []

        # This is a simplified action generation
        # In a real system, this would use more sophisticated planning
        goal_type = goal.get("type", "generic")

        if goal_type == "task":
            actions = [
                {
                    "action": "analyze",
                    "value": 0.7,
                    "description": "Analyze the task requirements",
                },
                {
                    "action": "plan",
                    "value": 0.8,
                    "description": "Create a detailed plan",
                },
                {
                    "action": "execute",
                    "value": 0.6,
                    "description": "Execute the planned steps",
                },
                {
                    "action": "review",
                    "value": 0.5,
                    "description": "Review progress and adjust",
                },
            ]
        elif goal_type == "learning":
            actions = [
                {
                    "action": "study",
                    "value": 0.8,
                    "description": "Study relevant materials",
                },
                {
                    "action": "practice",
                    "value": 0.7,
                    "description": "Practice the skill",
                },
                {"action": "test", "value": 0.6, "description": "Test understanding"},
                {
                    "action": "reflect",
                    "value": 0.5,
                    "description": "Reflect on learning",
                },
            ]

        return actions

    def _simulate_action(
        self, state: Dict[str, Any], action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate the outcome of an action.

        Creates a new state by applying the effects of an action. This is a
        simplified simulation for planning purposes.

        Args:
            state (Dict[str, Any]): Current state.
            action (Dict[str, Any]): Action to simulate, containing 'action' field.

        Returns:
            Dict[str, Any]: New state after action simulation.

        Supported Actions:
            - 'analyze': Sets 'analyzed' = True
            - 'plan': Sets 'planned' = True
            - 'execute': Sets 'executed' = True
            - 'review': Sets 'reviewed' = True
        """
        new_state = state.copy()
        action_type = action.get("action", "")

        # Simple state transitions
        if action_type == "analyze":
            new_state["analyzed"] = True
        elif action_type == "plan":
            new_state["planned"] = True
        elif action_type == "execute":
            new_state["executed"] = True
        elif action_type == "review":
            new_state["reviewed"] = True

        return new_state

    def _goal_achieved(self, state: Dict[str, Any], goal: Dict[str, Any]) -> bool:
        """
        Check if goal has been achieved.

        Compares current state against goal criteria to determine achievement.

        Args:
            state (Dict[str, Any]): Current state.
            goal (Dict[str, Any]): Goal containing 'criteria' field with required state.

        Returns:
            bool: True if all goal criteria are met, False otherwise.
        """
        goal_criteria = goal.get("criteria", {})
        for key, value in goal_criteria.items():
            if state.get(key) != value:
                return False
        return True

    def _options_similar(
        self, option1: Dict[str, Any], option2: Dict[str, Any]
    ) -> bool:
        """
        Check if two options are similar.

        Determines similarity by checking for matching key fields.

        Args:
            option1 (Dict[str, Any]): First option to compare.
            option2 (Dict[str, Any]): Second option to compare.

        Returns:
            bool: True if options share any key field values.
        """
        keys_to_check = ["action", "task", "goal"]
        for key in keys_to_check:
            if option1.get(key) == option2.get(key):
                return True
        return False

    def get_working_memory(self) -> List[Dict[str, Any]]:
        """
        Get current working memory contents.

        Returns a copy of the current working memory items for inspection.

        Returns:
            List[Dict[str, Any]]: Copy of current working memory contents.
        """
        return self.working_memory.copy()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get prefrontal cortex statistics.

        Returns comprehensive statistics about the current state of executive functions.

        Returns:
            Dict[str, Any]: Statistics dictionary containing:
                - wm_capacity: Current working memory usage
                - wm_max_capacity: Maximum working memory capacity
                - active_goals: Number of active goals
                - decision_history_length: Length of decision history
                - inhibition_buffer_size: Size of inhibition buffer
        """
        return {
            "wm_capacity": len(self.working_memory),
            "wm_max_capacity": self.cfg.working_memory_capacity,
            "active_goals": len(self.active_goals),
            "decision_history_length": len(self.decision_history),
            "inhibition_buffer_size": len(self.inhibition_buffer),
        }
