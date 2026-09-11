"""Static source facts used only when retained runtime evidence is insufficient."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_MAX_EXERCISES = 5
_MAX_CHECKS = 6
_MAX_PROOF_CHECKS = 3
_MAX_CALL_DISPLAY = 120
_HUMAN_TOKENS = {
    "ai": "AI",
    "api": "API",
    "e2e": "E2E",
    "genai": "GenAI",
    "http": "HTTP",
    "https": "HTTPS",
    "id": "ID",
    "json": "JSON",
    "openai": "OpenAI",
    "pytest": "Pytest",
    "qwenchat": "QwenChat",
    "sdk": "SDK",
    "url": "URL",
}
_SUBJECT_IGNORED = {
    "FakeClient",
    "ScriptedHTTPServer",
    "ScriptedResponse",
    "TemporaryDirectory",
    "Path",
    "build_default_config",
    "loads",
    "recorded_requests",
    "request_count",
    "replace",
    "setenv",
    "delenv",
    "write_text",
    "write_bytes",
    "read_text",
    "read_bytes",
}
_SUBJECT_PREFERRED = (
    "execute",
    "query",
    "resolve",
    "validate",
    "normalize",
    "classify",
    "build_repair",
    "install",
    "get_config",
    "save",
    "load",
)


def human_words(value: str) -> str:
    """Humanize identifiers while preserving common technical acronyms."""
    words = [
        _HUMAN_TOKENS.get(word.casefold(), word)
        for word in value.replace("_", " ").split()
    ]
    text = " ".join(words)
    return text[:1].upper() + text[1:] if text else value


def module_title(path: str) -> str:
    """Humanize a test module name without pytest naming noise."""
    stem = Path(path).stem
    for prefix in ("test_internal_", "test_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    for suffix in ("_fake_server", "_fake"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return human_words(stem)


def _compact(value: str, *, limit: int = 180) -> str:
    """Normalize one source fragment for compact display."""
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _unparse(node: ast.AST) -> str:
    """Safely unparse one AST node into compact source."""
    try:
        return _compact(ast.unparse(node))
    except (ValueError, TypeError):
        return ""


def _call_name(call: ast.Call) -> str:
    """Return the terminal callable name for one call."""
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def _display_call(call: ast.Call) -> str:
    """Render one call without letting large literals dominate."""
    source = _unparse(call)
    if len(source) <= _MAX_CALL_DISPLAY:
        return source
    name = _call_name(call)
    return f"{name}(…)" if name else source


def _inside(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    kind: type[ast.AST],
) -> bool:
    """Return whether a node is nested below an ancestor of the given kind."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, kind):
            return True
        current = parents.get(current)
    return False


def _exercise_source(
    node: ast.AST,
    *,
    parents: dict[ast.AST, ast.AST],
    decorator_nodes: set[ast.AST],
) -> str:
    """Return one top-level executable call suitable for the narrative."""
    ignored = {
        "raises",
        "len",
        "isinstance",
        "str",
        "int",
        "bool",
        "list",
        "dict",
        "tuple",
        "set",
    }
    if not isinstance(node, ast.Call) or node in decorator_nodes:
        return ""
    if _inside(node, parents, ast.Assert) or _inside(node, parents, ast.Call):
        return ""
    if _call_name(node) in ignored:
        return ""
    return _display_call(node)


def extract_exercises(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    """Extract important executable calls from one test body."""
    parents = {
        child: parent
        for parent in ast.walk(function)
        for child in ast.iter_child_nodes(parent)
    }
    decorator_nodes = {
        node for decorator in function.decorator_list for node in ast.walk(decorator)
    }
    values: list[str] = []
    for node in ast.walk(function):
        source = _exercise_source(
            node,
            parents=parents,
            decorator_nodes=decorator_nodes,
        )
        if source and source not in values:
            values.append(source)
        if len(values) >= _MAX_EXERCISES:
            break
    return tuple(values)


def _checks_from_node(node: ast.AST) -> tuple[str, ...]:
    """Return assertion-style proof fragments represented by one AST node."""
    if isinstance(node, ast.Assert):
        source = _unparse(node.test)
        return (source,) if source else ()
    if not isinstance(node, (ast.With, ast.AsyncWith)):
        return ()
    values: list[str] = []
    for item in node.items:
        context = item.context_expr
        if (
            isinstance(context, ast.Call)
            and _call_name(context) == "raises"
            and context.args
        ):
            values.append(f"raises {_unparse(context.args[0])}")
    return tuple(values)


def extract_checks(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    """Extract explicit assertions and expected exceptions."""
    checks: list[str] = []
    for node in ast.walk(function):
        checks.extend(_checks_from_node(node))
        if len(checks) >= _MAX_CHECKS:
            break
    return tuple(dict.fromkeys(checks))


def extract_generated_inputs(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    """Extract Hypothesis given strategies when present."""
    values: list[str] = []
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or _call_name(decorator) != "given":
            continue
        values.extend(
            f"{keyword.arg} = {_unparse(keyword.value)}"
            for keyword in decorator.keywords
            if keyword.arg is not None
        )
        values.extend(_unparse(argument) for argument in decorator.args)
    return tuple(value for value in values if value)


def _subject_score(name: str) -> int:
    """Score one callable name by production relevance."""
    if name in _SUBJECT_IGNORED or name.startswith("_"):
        return 0
    if any(token in name.casefold() for token in _SUBJECT_PREFERRED):
        return 4
    return 2 if name[:1].isupper() else 1


def _qualified_subjects(exercise: str, order: int) -> list[tuple[int, int, str]]:
    """Return explicit Class.method calls with highest subject priority."""
    patterns = (
        r"\b([A-Z][A-Za-z0-9_]*)\([^)]*\)\.([A-Za-z_][A-Za-z0-9_]*)\(",
        r"\b([A-Z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\(",
    )
    values: list[tuple[int, int, str]] = []
    for pattern in patterns:
        match = re.search(pattern, exercise)
        if match is not None:
            values.append((6, order, f"{match.group(1)}.{match.group(2)}()"))
    return values


def _named_subjects(exercise: str, order: int) -> list[tuple[int, int, str]]:
    """Return scored simple callable names from one exercise."""
    values: list[tuple[int, int, str]] = []
    for name in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", exercise):
        score = _subject_score(name)
        if score:
            values.append((score, order, f"{name}()"))
    return values


def subject(exercises: tuple[str, ...]) -> str:
    """Pick the production-facing operation instead of test/setup plumbing."""
    candidates: list[tuple[int, int, str]] = []
    for order, exercise in enumerate(exercises):
        candidates.extend(_qualified_subjects(exercise, order))
        candidates.extend(_named_subjects(exercise, order))
    if not candidates:
        return "production subject"
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def observed_proof(checks: tuple[str, ...]) -> str:
    """Summarize explicit assertions without inventing additional semantics."""
    if not checks:
        return "The explicit assertions shown below."
    shown = " · ".join(checks[:_MAX_PROOF_CHECKS])
    return f"{shown} · …" if len(checks) > _MAX_PROOF_CHECKS else shown


def test_double_names(code: str) -> tuple[str, ...]:
    """Return explicit fake/test-double constructors visible in the testcase."""
    return tuple(dict.fromkeys(re.findall(r"\b(Fake[A-Z][A-Za-z0-9_]*)\s*\(", code)))
