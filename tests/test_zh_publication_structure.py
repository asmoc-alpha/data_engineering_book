from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import export_ustc_press_submission_package as ustc_export
import export_zh_book_latex as zh_export


def flatten_nav(items):
    for item in items:
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    yield value
                elif isinstance(value, list):
                    yield from flatten_nav(value)


class ChinesePublicationStructureTest(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        self.zh_nav = next(
            lang["nav"]
            for lang in self.config["plugins"][2]["i18n"]["languages"]
            if lang["locale"] == "zh"
        )

    def test_all_chinese_chapter_files_are_in_mkdocs_nav(self):
        chapter_paths = sorted(
            path.relative_to(ROOT / "docs/zh").as_posix()
            for path in (ROOT / "docs/zh").glob("part*/ch*.md")
        )
        nav_paths = set(flatten_nav(self.zh_nav))

        missing = [path for path in chapter_paths if path not in nav_paths]

        self.assertEqual(missing, [])

    def test_all_chinese_chapter_files_are_in_book_index(self):
        index_text = (ROOT / "docs/zh/index.md").read_text(encoding="utf-8")
        chapter_paths = sorted(
            path.relative_to(ROOT / "docs/zh").as_posix()
            for path in (ROOT / "docs/zh").glob("part*/ch*.md")
        )

        missing = [path for path in chapter_paths if f"]({path})" not in index_text]

        self.assertEqual(missing, [])

    def test_chinese_chapter_numbers_are_unique(self):
        seen: dict[int, str] = {}
        duplicates: list[tuple[int, str, str]] = []

        for path in sorted((ROOT / "docs/zh").glob("part*/ch*.md")):
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            first_line = next((line for line in lines if line.startswith("# ")), "")
            match = re.search(r"第(\d+)章", first_line)
            self.assertIsNotNone(match, f"{path} missing chapter number in title")
            chapter_no = int(match.group(1))
            rel = path.relative_to(ROOT).as_posix()
            if chapter_no in seen:
                duplicates.append((chapter_no, seen[chapter_no], rel))
            else:
                seen[chapter_no] = rel

        self.assertEqual(duplicates, [])

    def test_chinese_export_covers_use_the_chinese_title_page_authors(self):
        expected = (
            "於俊、陈长汶、于璠、王聪、骆阳、张然、杜文卓、徐鑫、王柯、汪志立、"
            "刘中一、曹旭宏、穆冠霖、刘冠钧、邹越峰、徐麟、陈新宇、陈凤欣、李轩、"
            "赵功鹏、王灿、赵凤、余烨、高放、梁家恩、黄伟、刘升平、刘青松、孙见青"
        )
        stats = zh_export.ExportStats()

        self.assertEqual(zh_export.chinese_book_authors(), expected)
        self.assertIn(expected, zh_export.latex_preamble(stats))
        self.assertIn(expected, ustc_export.ustc_preamble(stats))
        self.assertIn(expected, ustc_export.build_wrapper([], stats))

        for rendered in (
            zh_export.latex_preamble(stats),
            ustc_export.ustc_preamble(stats),
            ustc_export.build_wrapper([], stats),
        ):
            self.assertNotRegex(rendered, r"Gongpeng Zhao|Feng Zhao|Ye Yu|Fang Gao")

    def test_publication_captions_are_centered_in_chinese_latex(self):
        stats = zh_export.ExportStats()
        assets = zh_export.AssetManager(ROOT / "output" / "test-caption-assets", stats)
        source = ROOT / "docs" / "zh" / "part1" / "ch02_quality_framework.md"
        markdown = "\n\n".join(
            [
                "*图 2-1：生命周期视角下的多维度质量分层架构*",
                "*表2-1：四阶段质量目标演变矩阵*",
                "*代码清单P06-1：流程示例*",
            ]
        )

        rendered = zh_export.markdown_to_latex(markdown, source, assets, stats, ROOT / "output")

        self.assertEqual(rendered.count(r"\begin{bookcaption}"), 3)
        self.assertEqual(rendered.count(r"\end{bookcaption}"), 3)
        self.assertNotIn(r"\emph{图 2-", rendered)
        self.assertNotIn(r"\emph{表2-", rendered)
        self.assertNotIn(r"\emph{代码清单P06-", rendered)


if __name__ == "__main__":
    unittest.main()
