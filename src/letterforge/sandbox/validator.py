from __future__ import annotations

import ast

_BLOCKED_MODULES = {
    "subprocess", "socket", "shutil", "ctypes", "importlib",
    "multiprocessing", "threading", "pty", "atexit", "signal",
}
_BLOCKED_BUILTINS = {"exec", "eval", "compile", "__import__", "breakpoint"}


def validate_generated_code(code: str) -> list[str]:
    """
    Returns a list of violation strings. Empty list means the code is safe to run.
    Raises SyntaxError if the code cannot be parsed.
    """
    tree = ast.parse(code)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BLOCKED_MODULES:
                    violations.append(f"Blocked import: {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in _BLOCKED_MODULES:
                    violations.append(f"Blocked import from: {node.module}")

        elif isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _BLOCKED_BUILTINS:
                violations.append(f"Blocked call: {name}()")

    return violations
