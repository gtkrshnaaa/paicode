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


ROSTER = [
    AgentRole(1, "lead", "Lead Architect", "Chairs the council, freezes the contract, owns shared files, and arbitrates conflicts."),
    AgentRole(2, "frontend-shell", "Frontend Shell", "Owns routing, page composition, and application entry points."),
    AgentRole(3, "ui-components", "UI Components", "Owns interactive components, forms, and component states."),
    AgentRole(4, "design-system", "Design System", "Owns layout, CSS tokens, responsive rules, and visual consistency."),
    AgentRole(5, "client-state", "Client State", "Owns client state, data flow, and loading and error states."),
    AgentRole(6, "api-client", "API Client", "Owns request and response contracts and client transport."),
    AgentRole(7, "backend-http", "Backend HTTP", "Owns routes, handlers, middleware, and HTTP status behavior."),
    AgentRole(8, "domain-services", "Domain Services", "Owns business rules and service boundaries."),
    AgentRole(9, "database", "Database", "Owns schema, migrations, indexes, and queries."),
    AgentRole(10, "auth-security", "Auth and Security", "Owns authentication, authorization, and secret handling."),
    AgentRole(11, "validation", "Validation and Errors", "Owns input validation, error mapping, and edge cases."),
    AgentRole(12, "test-architect", "Test Architect", "Owns acceptance criteria and the test matrix."),
    AgentRole(13, "test-implementer", "Test Implementer", "Owns test files, fixtures, and integration tests."),
    AgentRole(14, "integration", "Integration", "Owns wiring, shared boundaries, and cross-module contracts."),
    AgentRole(15, "accessibility", "Accessibility", "Owns keyboard behavior, focus management, and accessibility."),
    AgentRole(16, "performance", "Performance", "Owns caching, query efficiency, and runtime performance."),
    AgentRole(17, "devops", "DevOps", "Owns scripts, environment setup, and build commands."),
    AgentRole(18, "docs", "Documentation", "Owns developer-facing documentation and usage notes."),
    AgentRole(19, "data", "Data and Fixtures", "Owns seed data, fixtures, and local development data."),
    AgentRole(20, "quality", "Refactor and Quality", "Owns naming, duplication, and code quality."),
    AgentRole(21, "observability", "Observability", "Owns logging, diagnostics, and failure visibility."),
    AgentRole(22, "validator", "Validator", "Independently tests the integrated result and gates release."),
]

ROLE_BY_ID = {role.id: role for role in ROSTER}
BUILDER_IDS = tuple(role.id for role in ROSTER if role.is_builder)


def role_for(agent_id: int) -> AgentRole:
    return ROLE_BY_ID[int(agent_id)]
