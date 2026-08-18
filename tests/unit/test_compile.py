from pathlib import Path
import py_compile


ROOT = Path(__file__).resolve().parents[2]


def test_all_python_files_compile():
    python_files = [
        path
        for path in ROOT.rglob("*.py")
        if ".venv" not in path.parts
        and "venv" not in path.parts
        and "__pycache__" not in path.parts
    ]

    assert python_files

    for path in python_files:
        py_compile.compile(
            str(path),
            doraise=True,
        )
