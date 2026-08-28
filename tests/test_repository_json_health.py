"""Repository-wide JSON health checks.

These tests are intentionally dependency-free so merge mistakes in profile/data files
are caught before the Pygame launcher tries to start.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSON_ROOTS = (ROOT / "profiles", ROOT / "res")
MERGE_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
RUNTIME_DIR_NAMES = {"_backups", "_backup", "_tmp", "_temp"}


def _is_runtime_artifact(path: Path) -> bool:
    return any(part in RUNTIME_DIR_NAMES for part in path.parts)


class RepositoryJsonHealthTests(unittest.TestCase):
    def test_tracked_json_has_no_merge_markers_and_parses(self) -> None:
        problems: list[str] = []

        for json_root in JSON_ROOTS:
            if not json_root.exists():
                continue

            for path in sorted(json_root.rglob("*.json")):
                if _is_runtime_artifact(path):
                    continue

                text = path.read_text(encoding="utf-8")
                relative = path.relative_to(ROOT)

                markers = [marker for marker in MERGE_MARKERS if marker in text]
                if markers:
                    problems.append(
                        f"{relative}: unresolved merge marker(s): {', '.join(markers)}"
                    )
                    continue

                try:
                    json.loads(text)
                except json.JSONDecodeError as exc:
                    problems.append(
                        f"{relative}: invalid JSON at line {exc.lineno}, "
                        f"column {exc.colno}: {exc.msg}"
                    )

        self.assertFalse(problems, "\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
