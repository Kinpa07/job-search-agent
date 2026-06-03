from typing import Literal

# Constrained value sets shared across the ORM models, parser tool schemas, and API
# schemas so the layers can't drift. These are Literal aliases (not enum.Enum) —
# enforced by Pydantic/mypy at every boundary, stored in plain VARCHAR columns, and
# evolvable without a migration. Mirrors the `status` Literal on UserProfile.

ProficiencyLevel = Literal["familiar", "proficient", "expert"]
