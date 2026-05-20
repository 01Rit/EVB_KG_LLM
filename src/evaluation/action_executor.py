"""Action executor: applies OptimizationAction graph operations to subgraphs."""
import copy
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    OptimizationAction, OptimizationActionCreate, ActionOperation, ActionStatus,
)

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Applies graph operations to create new DesignVersion subgraphs."""

    def __init__(self):
        self._actions: dict[str, OptimizationAction] = {}

    def create_action(self, assessment_id: str, data: OptimizationActionCreate) -> OptimizationAction:
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        action = OptimizationAction(
            action_id=action_id,
            assessment_id=assessment_id,
            operation=data.operation,
            target_label=data.target_label,
            target_id=data.target_id,
            payload=data.payload,
            reason=data.reason,
            status=ActionStatus.PROPOSED,
        )
        self._actions[action_id] = action
        return action

    def get_actions(self, assessment_id: str) -> list[OptimizationAction]:
        return [a for a in self._actions.values() if a.assessment_id == assessment_id]

    def apply_action(self, subgraph: dict, action: OptimizationAction) -> dict:
        """Apply a single action to a subgraph, returning a NEW subgraph (no mutation)."""
        new_sg = copy.deepcopy(subgraph)
        try:
            if action.operation == ActionOperation.ADD_NODE:
                self._apply_add_node(new_sg, action)
            elif action.operation == ActionOperation.REMOVE_NODE:
                self._apply_remove_node(new_sg, action)
            elif action.operation == ActionOperation.MODIFY_PROPERTY:
                self._apply_modify_property(new_sg, action)
            elif action.operation == ActionOperation.ADD_REL:
                self._apply_add_rel(new_sg, action)
            elif action.operation == ActionOperation.REMOVE_REL:
                self._apply_remove_rel(new_sg, action)
            elif action.operation == ActionOperation.SWAP_CONNECTION:
                self._apply_swap_connection(new_sg, action)
            else:
                logger.warning(f"Unknown operation: {action.operation}")
        except Exception as e:
            logger.error(f"Failed to apply action {action.action_id}: {e}")
        return new_sg

    def apply_actions(self, subgraph: dict, actions: list[OptimizationAction]) -> dict:
        current = copy.deepcopy(subgraph)
        for action in actions:
            if action.status != ActionStatus.PROPOSED:
                continue
            current = self.apply_action(current, action)
        return current

    def mark_applied(self, action_id: str) -> Optional[OptimizationAction]:
        action = self._actions.get(action_id)
        if action:
            updated = action.model_copy(update={"status": ActionStatus.APPLIED})
            self._actions[action_id] = updated
            return updated
        return None

    def mark_rejected(self, action_id: str) -> Optional[OptimizationAction]:
        action = self._actions.get(action_id)
        if action:
            updated = action.model_copy(update={"status": ActionStatus.REJECTED})
            self._actions[action_id] = updated
            return updated
        return None

    def _apply_add_node(self, subgraph: dict, action: OptimizationAction):
        node = action.payload.copy()
        node.setdefault("id", f"new_{uuid.uuid4().hex[:8]}")
        node.setdefault("labels", [action.target_label] if action.target_label else [])
        subgraph["nodes"].append(node)

    def _apply_remove_node(self, subgraph: dict, action: OptimizationAction):
        tid = action.target_id
        subgraph["nodes"] = [n for n in subgraph["nodes"] if n.get("id") != tid]
        subgraph["relationships"] = [
            r for r in subgraph["relationships"]
            if r.get("start") != tid and r.get("end") != tid
        ]

    def _apply_modify_property(self, subgraph: dict, action: OptimizationAction):
        tid = action.target_id
        prop = action.payload.get("property", "")
        new_val = action.payload.get("new_value")
        for node in subgraph["nodes"]:
            if node.get("id") == tid:
                node[prop] = new_val

    def _apply_add_rel(self, subgraph: dict, action: OptimizationAction):
        rel = {
            "start": action.payload.get("start", ""),
            "end": action.payload.get("end", ""),
            "type": action.payload.get("type", ""),
        }
        subgraph["relationships"].append(rel)

    def _apply_remove_rel(self, subgraph: dict, action: OptimizationAction):
        subgraph["relationships"] = [
            r for r in subgraph["relationships"]
            if not (
                r.get("start") == action.payload.get("start")
                and r.get("end") == action.payload.get("end")
                and r.get("type") == action.payload.get("type")
            )
        ]

    def _apply_swap_connection(self, subgraph: dict, action: OptimizationAction):
        remove = action.payload.get("remove_rel", {})
        add = action.payload.get("add_rel", {})
        subgraph["relationships"] = [
            r for r in subgraph["relationships"]
            if not (
                r.get("start") == remove.get("start")
                and r.get("end") == remove.get("end")
                and r.get("type") == remove.get("type")
            )
        ]
        subgraph["relationships"].append({
            "start": add.get("start", ""),
            "end": add.get("end", ""),
            "type": add.get("type", ""),
        })
