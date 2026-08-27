from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "reference_library.py"
SPEC = importlib.util.spec_from_file_location("reference_library", SCRIPT_PATH)
assert SPEC and SPEC.loader
reference_library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reference_library)


class ReferenceLibraryTests(unittest.TestCase):
    def test_bundled_starter_library_is_searchable_without_config(self) -> None:
        records = reference_library.combined_records()

        self.assertEqual(52, len(records))
        self.assertEqual(
            {"creator", "starter"}, {record["library"] for record in records}
        )
        self.assertEqual(48, sum(record["library"] == "creator" for record in records))
        self.assertEqual(4, sum(record["library"] == "starter" for record in records))
        matches = reference_library.search_records(records, "章节标题", False)
        self.assertEqual(["cbb79775b708"], [record["id"] for record in matches])

    def test_creator_library_has_rights_metadata_and_prebuilt_video_previews(self) -> None:
        records = reference_library.combined_records()
        creator_records = [record for record in records if record["library"] == "creator"]
        video = next(record for record in creator_records if record["kind"] == "video")

        self.assertEqual({"CC-BY-NC-4.0"}, {record["license"] for record in creator_records})
        self.assertEqual({"Work-Fisher"}, {record["creator"] for record in creator_records})
        preview = reference_library.create_preview(
            Path(video["_library_root"]), video, 24
        )

        self.assertTrue(preview["prebuilt"])
        self.assertEqual(12, preview["frames"])
        self.assertTrue(Path(preview["preview"]).is_file())

    def test_bundled_video_preview_uses_prebuilt_contact_sheet(self) -> None:
        record = reference_library.find_record(
            reference_library.combined_records(), "14e6e2e2636c"
        )

        preview = reference_library.create_preview(
            reference_library.starter_root(), record, 24
        )

        self.assertTrue(preview["prebuilt"])
        self.assertEqual(12, preview["frames"])
        self.assertTrue(Path(preview["preview"]).is_file())

    def test_missing_config_keeps_personal_roots_optional(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "missing.json"

            self.assertIsNone(
                reference_library.optional_library_root(config_file=str(config))
            )
            self.assertIsNone(
                reference_library.optional_learning_root(config_file=str(config))
            )

    def test_personal_records_extend_and_take_priority_over_starter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            personal = Path(temporary)
            (personal / "personal.jpg").write_bytes(b"personal-reference")
            reference_library.build_index(personal)

            records = reference_library.combined_records(personal)

            self.assertEqual(53, len(records))
            self.assertEqual("personal", records[0]["library"])
            self.assertEqual(48, sum(record["library"] == "creator" for record in records))
            self.assertEqual(4, sum(record["library"] == "starter" for record in records))

    def test_external_config_supplies_machine_specific_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            config = base / "motion-director.json"
            reference_root = base / "references"
            learning_root = base / "learning"
            config.write_text(
                json.dumps(
                    {
                        "reference_library": str(reference_root),
                        "learning_root": str(learning_root),
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                reference_root,
                reference_library.library_root(config_file=str(config)),
            )
            self.assertEqual(
                learning_root,
                reference_library.learning_root(config_file=str(config)),
            )

    def test_index_deduplicates_content_and_skips_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.jpg").write_bytes(b"same-image")
            (root / "copy.jpg").write_bytes(b"same-image")
            (root / "clip.mp4").write_bytes(b"video")
            metadata = root / "_library"
            metadata.mkdir()
            (metadata / "ignored.jpg").write_bytes(b"ignore-me")

            records = reference_library.build_index(root)

            self.assertEqual(2, len(records))
            image = next(record for record in records if record["kind"] == "image")
            self.assertEqual("a.jpg", image["path"])
            self.assertEqual(["copy.jpg"], image["aliases"])
            self.assertTrue(reference_library.index_path(root).exists())

    def test_add_is_non_destructive_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as library_temp, tempfile.TemporaryDirectory() as source_temp:
            root = Path(library_temp)
            source = Path(source_temp) / "new.jpg"
            source.write_bytes(b"new-reference")

            first = reference_library.add_file(root, source)
            second = reference_library.add_file(root, source)

            self.assertEqual("copied", first["status"])
            self.assertEqual("deduplicated", second["status"])
            self.assertTrue(source.exists())
            self.assertTrue((root / "new.jpg").exists())

    def test_annotations_survive_reindex_and_are_searchable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "optical.jpg").write_bytes(b"optical")
            records = reference_library.build_index(root)
            asset_id = records[0]["id"]
            reference_library.annotate_record(
                root,
                asset_id,
                {
                    "summary": "黑底光学字体",
                    "tags": ["黑底", "光学", "字体"],
                    "palette": "青蓝折射光",
                },
            )

            rebuilt = reference_library.build_index(root)
            matches = reference_library.search_records(rebuilt, "光学 字体", False)

            self.assertTrue(rebuilt[0]["reviewed"])
            self.assertEqual("黑底光学字体", rebuilt[0]["summary"])
            self.assertEqual([asset_id], [record["id"] for record in matches])

    def test_same_name_different_content_is_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as library_temp, tempfile.TemporaryDirectory() as source_temp:
            root = Path(library_temp)
            (root / "same.jpg").write_bytes(b"old")
            source = Path(source_temp) / "same.jpg"
            source.write_bytes(b"new")

            result = reference_library.add_file(root, source)

            self.assertEqual("copied", result["status"])
            self.assertTrue((root / "same__v2.jpg").exists())
            self.assertEqual(b"old", (root / "same.jpg").read_bytes())
            self.assertEqual(b"new", (root / "same__v2.jpg").read_bytes())


if __name__ == "__main__":
    unittest.main()
