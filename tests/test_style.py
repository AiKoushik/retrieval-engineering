"""The book prints these files: short lines, balanced regions."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX = 76
SKIP = {"data", ".pytest_cache", "__pycache__", ".git"}
PRINTED = {".py", ".sql", ".md", ".toml", ".yml"}
OPEN, CLOSE = "region" + ":", "endregion" + ":"
MARKER = re.compile(r"^\s*(#|--) (end)?region: ([a-z0-9][a-z0-9-]*)$")
MENTION = re.compile(r"(#|--) (end)?region:")


def source_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file()
                  and not SKIP & set(p.relative_to(ROOT).parts)
                  and (p.suffix in PRINTED or p.name == "Makefile"))


def test_every_line_fits_the_page():
    long = [f"{p.relative_to(ROOT)}:{i}: {len(line)}"
            for p in source_files()
            for i, line in enumerate(p.read_text().splitlines(), 1)
            if len(line) > MAX]
    assert not long, "\n".join(long)


def check_regions(path: Path) -> list[str]:
    problems, stack, seen = [], [], set()
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not MENTION.search(line):
            continue
        m = MARKER.match(line)
        if not m:
            problems.append(f"{path.name}:{i}: marker not on own line")
            continue
        name = m.group(3)
        if m.group(2) is None:
            if name in seen:
                problems.append(f"{path.name}:{i}: duplicate {name}")
            seen.add(name)
            stack.append(name)
        elif not stack or stack.pop() != name:
            problems.append(f"{path.name}:{i}: unbalanced {name}")
    problems += [f"{path.name}: {n} never closed" for n in stack]
    return problems


def test_region_markers_are_balanced_and_unique():
    problems = [p for f in source_files() if f.suffix in (".py", ".sql")
                for p in check_regions(f)]
    assert not problems, "\n".join(problems)
    rx_files = list((ROOT / "rx").glob("*.py")) + [ROOT / "sql" /
                                                   "001_core.sql"]
    assert all(OPEN in f.read_text() for f in rx_files
               if f.name != "__init__.py")
    assert CLOSE


def test_the_checker_catches_mistakes(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text(f"# {OPEN} a\n# {OPEN} b\n# {CLOSE} a\n"
                   f"x = 1  # {OPEN} c\n")
    problems = check_regions(bad)
    assert any("unbalanced a" in p for p in problems)
    assert any("own line" in p for p in problems)
