from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    path: str = "$"


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def raise_for_errors(self) -> None:
        if self.issues:
            raise EntityValidationError(self)


class EntityValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in report.issues)
        super().__init__(f"Entity validation failed: {details}")


class ValidatableEntity(Protocol):
    entity_id: str


class ValidationRule(Protocol):
    def __call__(self, entity: ValidatableEntity) -> Sequence[ValidationIssue]: ...


class Validator:
    def __init__(self, rules: Sequence[ValidationRule] = ()) -> None:
        self._rules = tuple(rules)

    def validate(self, entity: ValidatableEntity) -> ValidationReport:
        issues: list[ValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule(entity))
        return ValidationReport(tuple(issues))

