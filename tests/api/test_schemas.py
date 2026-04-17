import pytest
from src.api.schemas import Step


def test_step_has_scoring_fields():
    step = Step(
        id=1,
        component="Battery壳体",
        action="拆卸外壳",
        tool=["螺丝刀"],
        h_score=0.65,
        s_score=0.42,
        as_score=0.535,
        human_loss=2.0,
        robot_loss=1.0,
        loss_diff=1.0,
        assignee="human"
    )
    assert step.h_score == 0.65
    assert step.assignee == "human"