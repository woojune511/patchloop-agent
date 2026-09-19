"""Optional, bounded syntax evidence for model-selected probe construction claims."""
from __future__ import annotations

import ast
import keyword
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator

from patchloop.dev.tools import DevToolGateway
from patchloop.util import sha256_bytes, sha256_json

MODE = "direct-links-v1"
MAX_LINKS = 4
MAX_STATEMENT_CHARS = 1600
MAX_REFERENCES = 32
NAME_PATTERN = r"^[A-Za-z_][A-Za-z_0-9]*$"
DESCRIPTION = (
    "Optionally use construction_links when applicability depends on how a value was obtained. "
    "Select a simple target variable assigned in python_source, the source variable you claim "
    "its right-hand expression directly references (or null), and a literal public requirement "
    "excerpt explaining relevance. Use line to select among repeated assignments, otherwise "
    "null. The host returns that exact statement and checks only direct name references. "
    "Reconcile this code with your applicability claim and expected_json if supplied. Missing "
    "or unknown references may need another alias/source inspection or a stated limitation. "
    "A reference does not prove copying, origin, runtime execution or correct expectations. "
    "Null leaves an ordinary probe; no link or extra probe is required to report."
)
INTERPRETATION = (
    "Syntax only: selected assignment and loaded names in its right-hand expression. "
    "No alias, factory, scope, control-flow or runtime value analysis. A present name does "
    "not prove derivation, copying or execution; an absent name does not rule out indirect "
    "derivation. Literal excerpt binding does not establish applicability or correctness."
)
Name = Annotated[str, Field(min_length=1, max_length=80, pattern=NAME_PATTERN)]


class ConstructionLink(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    target: Name
    source: Name | None
    line: int | None = Field(ge=1)
    requirement_excerpt: str = Field(min_length=1, max_length=600)

    @field_validator("target", "source")
    @classmethod
    def identifier(cls, value):
        if value is not None and keyword.iskeyword(value):
            raise ValueError("Python keyword is not a variable name")
        return value


LINKS = TypeAdapter(Annotated[list[ConstructionLink], Field(max_length=MAX_LINKS)])


def extend_schema(schema: dict) -> None:
    name = {"type": "string", "minLength": 1, "maxLength": 80, "pattern": NAME_PATTERN}
    properties = {
        "target": name,
        "source": {**name, "type": ["string", "null"]},
        "line": {"type": ["integer", "null"], "minimum": 1},
        "requirement_excerpt": {"type": "string", "minLength": 1, "maxLength": 600},
    }
    schema["description"] += " " + DESCRIPTION
    parameters = schema["parameters"]
    parameters["properties"]["construction_links"] = {
        "type": ["array", "null"], "maxItems": MAX_LINKS,
        "items": {"type": "object", "properties": properties, "required": list(properties),
                  "additionalProperties": False},
    }
    parameters["required"].append("construction_links")


def _inspect_link(link: ConstructionLink, tree: ast.AST, source: str, issue: str) -> dict:
    excerpt = " ".join(link.requirement_excerpt.split())
    result = {
        **link.model_dump(), "excerpt_matches_issue": bool(excerpt and excerpt in issue),
        "status": "unknown", "reason": None, "statement": None,
        "start_line": None, "end_line": None, "referenced_names": None,
        "direct_reference": None,
    }
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        if (any(isinstance(t, ast.Name) and t.id == link.target for t in targets)
                and (link.line is None or node.lineno == link.line)):
            assignments.append(node)
    if len(assignments) != 1:
        result.update(status="ambiguous" if assignments else "unknown",
                      reason="multiple_assignments" if assignments else "assignment_not_found")
        return result
    node = assignments[0]
    statement = ast.get_source_segment(source, node)
    if statement is None or len(statement) > MAX_STATEMENT_CHARS:
        result["reason"] = "statement_too_large_or_unavailable"
        return result
    result.update(statement=statement, start_line=node.lineno, end_line=node.end_lineno)
    # These expressions introduce bindings/scopes; a flat name walk would mislead.
    if any(isinstance(n, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                          ast.GeneratorExp, ast.NamedExpr)) for n in ast.walk(node.value)):
        result["reason"] = "unsupported_expression_scope"
        return result
    names = sorted({n.id for n in ast.walk(node.value)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)})
    if len(names) > MAX_REFERENCES or any(len(name) > 80 for name in names):
        result["reason"] = "references_too_large"
        return result
    result.update(status="inspected", referenced_names=names,
                  direct_reference=link.source in names if link.source is not None else None)
    return result


def inspect_links(python_source: str, construction_links, public_task) -> dict:
    receipt = {
        "mode": MODE, "status": "omitted", "reason": None, "links": [],
        "public_task_hash": sha256_json(public_task.model_dump(mode="json")),
        "interpretation": INTERPRETATION, "selection": "model_authored_unverified",
        "semantic_verdict": None, "coverage_status": "not_assessed",
        "next_question": (
            "Compare the selected code and direct references with the public requirement and "
            "your expected result. Resolve unsupported construction claims or state the limit; "
            "syntax evidence alone cannot validate origin or applicability."),
    }
    if construction_links is None:
        return receipt
    try:
        links = LINKS.validate_python(construction_links, strict=True)
    except ValidationError:
        return {**receipt, "status": "invalid", "reason": "invalid_construction_links"}
    if not links:
        return receipt
    if not isinstance(python_source, str) or not 1 <= len(python_source) <= 8000:
        return {**receipt, "status": "unknown", "reason": "source_outside_probe_bounds"}
    try:
        tree = ast.parse(python_source)
    except (SyntaxError, ValueError, RecursionError):
        return {**receipt, "status": "unknown", "reason": "source_not_parseable"}
    issue = " ".join((public_task.issue.title + " " + public_task.issue.description).split())
    return {**receipt, "status": "recorded",
            "links": [_inspect_link(link, tree, python_source, issue) for link in links]}


def gateway_type(base: type[DevToolGateway]) -> type[DevToolGateway]:
    class ConstructionLinksGateway(base):
        def _run_probe(self, question, python_source, *, construction_links=None, **kwargs):
            # Complete raw arguments are already frozen in the existing action journal.
            # Parse only; never execute submitted code on the host or pass links to the sandbox.
            receipt = inspect_links(python_source, construction_links, self.public_task)
            output = super()._run_probe(question, python_source, **kwargs)
            output["construction_evidence"] = {
                **receipt, "source_hash": sha256_bytes(python_source.encode()),
                "diff_hash": output["diff_hash"],
            }
            return output

    return ConstructionLinksGateway
