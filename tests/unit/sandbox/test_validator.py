import pytest

from letterforge.sandbox.validator import validate_generated_code


def test_clean_code_passes():
    code = """
import os
from pathlib import Path
from PIL import Image
import numpy as np

sheet1 = Image.open(os.environ["SHEET1_PATH"])
out = Path(os.environ["OUTPUT_DIR"])
sheet1.save(out / "upper_A.png")
"""
    assert validate_generated_code(code) == []


def test_subprocess_blocked():
    code = "import subprocess\nsubprocess.run(['ls'])"
    violations = validate_generated_code(code)
    assert any("subprocess" in v for v in violations)


def test_socket_blocked():
    code = "import socket\ns = socket.socket()"
    violations = validate_generated_code(code)
    assert any("socket" in v for v in violations)


def test_eval_blocked():
    code = "result = eval('1+1')"
    violations = validate_generated_code(code)
    assert any("eval" in v for v in violations)


def test_exec_blocked():
    code = "exec('import os')"
    violations = validate_generated_code(code)
    assert any("exec" in v for v in violations)


def test_shutil_blocked():
    code = "import shutil\nshutil.rmtree('/tmp')"
    violations = validate_generated_code(code)
    assert any("shutil" in v for v in violations)


def test_from_import_blocked():
    code = "from subprocess import run\nrun(['ls'])"
    violations = validate_generated_code(code)
    assert any("subprocess" in v for v in violations)


def test_syntax_error_raises():
    with pytest.raises(SyntaxError):
        validate_generated_code("def broken(:")


def test_multiple_violations():
    code = "import subprocess\nimport socket"
    violations = validate_generated_code(code)
    assert len(violations) >= 2


def test_ctypes_blocked():
    code = "import ctypes"
    violations = validate_generated_code(code)
    assert any("ctypes" in v for v in violations)
