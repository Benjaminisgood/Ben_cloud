from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.scripts.batch_ingest_tap_all_level_tags import SourceTag, build_tasks, load_unique_tags


class BatchIngestTapAllLevelTagsTests(unittest.TestCase):
    def test_load_unique_tags_collects_all_levels_and_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tap_all_levels.csv"
            csv_path.write_text(
                ",,,\n"
                "Level1,Level2,Level3\n"
                "Environment catalysis,VOCs,Au/SBA-15\n"
                "Environment catalysis,NOx reduction,Au/SBA-15\n"
                "Theory and model,VOCs,CeO2\n",
                encoding="utf-8",
            )

            tags = load_unique_tags(csv_path)

        self.assertEqual([item.tag for item in tags], [
            "Environment catalysis",
            "VOCs",
            "Au/SBA-15",
            "NOx reduction",
            "Theory and model",
            "CeO2",
        ])
        self.assertEqual(tags[0].source_levels, ["Level1"])
        self.assertEqual(tags[0].occurrence_count, 2)
        self.assertEqual(tags[1].source_levels, ["Level2"])
        self.assertEqual(tags[1].occurrence_count, 2)
        self.assertEqual(tags[2].source_levels, ["Level3"])
        self.assertEqual(tags[2].occurrence_count, 2)

    def test_load_unique_tags_rejects_incomplete_level_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tap_all_levels.csv"
            csv_path.write_text(
                "Level1,Level2,Level3\n"
                "Environment catalysis,VOCs,\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "缺少 Level1/Level2/Level3"):
                load_unique_tags(csv_path)

    def test_build_tasks_uses_tag_itself_as_query_and_save_tag(self) -> None:
        tasks = build_tasks(
            [
                SourceTag(
                    first_row_number=12,
                    tag="Oxidised Pd/Al2O3",
                    source_levels=["Level3"],
                    occurrence_count=3,
                    query_contexts=[],
                )
            ]
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].first_row_number, 12)
        self.assertEqual(tasks[0].query, "Oxidised Pd/Al2O3")
        self.assertEqual(tasks[0].save_tags, ["Oxidised Pd/Al2O3"])
        self.assertEqual(tasks[0].source_levels, ["Level3"])
        self.assertEqual(tasks[0].occurrence_count, 3)
        self.assertEqual(tasks[0].query_contexts, [])

    def test_load_unique_tags_does_not_mix_prompt_or_sibling_tags_into_query_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tap_all_levels.csv"
            csv_path.write_text(
                "Level1,Level2,Level3,Prompt\n"
                "Environment catalysis,VOCs,U3O8,查找采用 TAP 方法在 环境催化 领域研究 VOCs 反应并涉及 U3O8 的文献\n",
                encoding="utf-8",
            )

            tags = load_unique_tags(csv_path)

        u3o8 = next(item for item in tags if item.tag == "U3O8")
        self.assertEqual(u3o8.query_contexts, [])


if __name__ == "__main__":
    unittest.main()
