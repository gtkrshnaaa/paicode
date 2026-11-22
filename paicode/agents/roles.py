from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRole:
    id: int
    key: str
    title: str
    description: str

    @property
    def is_builder(self) -> bool:
        return 2 <= self.id <= 21


LEAD = AgentRole(
    1,
    "lead",
    "Lead",
    "Receives every prompt, triages scope, chairs the council, assigns one work unit per builder, owns shared files, integrates the board, and reports to the user.",
)
BUILDER = AgentRole(
    2,
    "builder",
    "Builder",
    "Universal builder. Owns one file or one cohesive sub-feature flow. No specialty. Works independently from the frozen contract and reports its patch.",
)
VALIDATOR = AgentRole(
    22,
    "validator",
    "Validator",
    "Independent validator. Runs the full test and ownership audit after every builder finishes, files strict findings to the owning builder, and gates release.",
)

ROSTER = [LEAD] + [
    AgentRole(agent_id, BUILDER.key, BUILDER.title, BUILDER.description)
    for agent_id in range(2, 22)
] + [VALIDATOR]
ROLE_BY_ID = {role.id: role for role in ROSTER}
BUILDER_IDS = tuple(role.id for role in ROSTER if role.is_builder)


def role_for(agent_id: int) -> AgentRole:
    return ROLE_BY_ID[int(agent_id)]


def role_label(agent_id: int) -> str:
    role = role_for(agent_id)
    return role.title
