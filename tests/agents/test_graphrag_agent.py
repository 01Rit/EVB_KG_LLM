"""
Test for GraphRAG Agent
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGraphRAGAgent:
    def test_task_creation(self):
        from agents.graphrag.agent import GraphRAGTask, create_graphrag_agent

        task = GraphRAGTask(
            task_type="plan",
            description="Test task",
            battery_model="18650",
            query="拆卸18650电池",
            context=["workspace A"],
            mode="local"
        )

        assert task.task_type == "plan"
        assert task.battery_model == "18650"
        assert task.mode == "local"

    def test_agent_factory(self):
        from agents.graphrag.agent import create_graphrag_agent

        agent = create_graphrag_agent(
            task_description="Test plan task",
            battery_model="18650",
            query="拆卸18650电池",
            task_type="plan"
        )

        assert agent is not None
        assert agent.task.task_type == "plan"
        assert agent.task.battery_model == "18650"

    def test_agent_factory_retrieve(self):
        from agents.graphrag.agent import create_graphrag_agent

        agent = create_graphrag_agent(
            task_description="Test retrieve task",
            battery_model="18650",
            query="电池外壳",
            task_type="retrieve"
        )

        assert agent.task.task_type == "retrieve"

    def test_agent_factory_rank(self):
        from agents.graphrag.agent import create_graphrag_agent

        agent = create_graphrag_agent(
            task_description="Test rank task",
            battery_model="18650",
            query="拆卸步骤",
            task_type="rank"
        )

        assert agent.task.task_type == "rank"

    def test_agent_factory_generate(self):
        from agents.graphrag.agent import create_graphrag_agent

        agent = create_graphrag_agent(
            task_description="Test generate task",
            battery_model="18650",
            query="拆卸步骤",
            context=["无"],
            task_type="generate"
        )

        assert agent.task.task_type == "generate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
