from .schema_agents import AGENT_MIGRATION
from .schema_core import CORE_MIGRATION

MIGRATIONS = [CORE_MIGRATION, AGENT_MIGRATION]

__all__ = ["MIGRATIONS"]
