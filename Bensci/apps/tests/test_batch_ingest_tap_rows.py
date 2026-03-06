from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.scripts.batch_ingest_tap_rows import SourceRow, build_tasks, load_source_rows


class BatchIngestTapRowsTests(unittest.TestCase):
    def test_load_source_rows_skips_leading_blank_csv_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tap_prompts.csv"
            csv_path.write_text(
                ",,,\n"
                "Level1,Level2,Level3,Prompt\n"
                'Environment catalysis,VOCs,Au/SBA-15,"使用自然语言 Prompt 检索"\n',
                encoding="utf-8",
            )

            rows = load_source_rows(csv_path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].row_number, 3)
        self.assertEqual(rows[0].level1, "Environment catalysis")
        self.assertEqual(rows[0].level2, "VOCs")
        self.assertEqual(rows[0].level3, "Au/SBA-15")
        self.assertEqual(rows[0].prompt, "使用自然语言 Prompt 检索")

    def test_load_source_rows_rejects_incomplete_data_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "tap_prompts.csv"
            csv_path.write_text(
                "Level1,Level2,Level3,Prompt\n"
                "Environment catalysis,VOCs,Au/SBA-15,\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "缺少 Level1/Level2/Level3/Prompt"):
                load_source_rows(csv_path)

    def test_build_tasks_uses_prompt_and_all_three_tags(self) -> None:
        tasks = build_tasks(
            [
                SourceRow(
                    row_number=12,
                    level1="Theory and model",
                    level2="CH4 reaction",
                    level3="Oxidised Pd/Al2O3",
                    prompt="查找采用 TAP 方法研究甲烷反应并涉及 Oxidised Pd/Al2O3 的文献",
                )
            ]
        )

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].row_number, 12)
        self.assertEqual(tasks[0].query, "查找采用 TAP 方法研究甲烷反应并涉及 Oxidised Pd/Al2O3 的文献")
        self.assertEqual(
            tasks[0].save_tags,
            ["Theory and model", "CH4 reaction", "Oxidised Pd/Al2O3"],
        )


if __name__ == "__main__":
    unittest.main()
