from __future__ import annotations

from tireless.llm.client import LocalLLM
from tireless.models import RoleName
from tireless.roles.barbara_minto import BarbaraMintoResearcher
from tireless.roles.base import Role
from tireless.roles.loop_builder import LoopBuilder
from tireless.roles.okr_creator import OKRCreator
from tireless.roles.slack_communicator import SlackCommunicator
from tireless.roles.test_engineer import TestEngineer
from tireless.roles.ux_builder import UXCXBuilder


def get_role(name: RoleName, llm: LocalLLM) -> Role:
    mapping: dict[RoleName, type[Role]] = {
        RoleName.LOOP_BUILDER: LoopBuilder,
        RoleName.OKR_CREATOR: OKRCreator,
        RoleName.BARBARA_MINTO: BarbaraMintoResearcher,
        RoleName.UX_CX_BUILDER: UXCXBuilder,
        RoleName.TEST_ENGINEER: TestEngineer,
        RoleName.SLACK_COMMUNICATOR: SlackCommunicator,
        RoleName.QUALITY_GATE: UXCXBuilder,  # quality is enforced inside UX builder + gate module
    }
    cls = mapping.get(name)
    if cls is None:
        raise KeyError(f"Unknown role: {name}")
    return cls(llm)
