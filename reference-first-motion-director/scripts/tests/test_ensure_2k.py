from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "ensure_2k.py"
SPEC = importlib.util.spec_from_file_location("ensure_2k", SCRIPT_PATH)
assert SPEC and SPEC.loader
ensure_2k = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ensure_2k)


class Ensure2KTests(unittest.TestCase):
    def test_exact_2k_source_is_copied_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            output = root / "final-2K.png"
            source.write_bytes(b"exact-2k")

            with patch.object(
                ensure_2k,
                "dimensions",
                side_effect=[(2048, 1152), (2048, 1152)],
            ):
                result = ensure_2k.produce_2k(source, output, False)

            self.assertEqual(b"exact-2k", output.read_bytes())
            self.assertEqual("copy", result["operation"])
            self.assertEqual("2048x1152", result["final_dimensions"])

    def test_16_by_9_source_is_resampled_with_lanczos(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.jpg"
            output = root / "final-2K.png"
            source.write_bytes(b"source")
            commands: list[list[str]] = []

            def fake_run(command: list[str]):
                commands.append(command)
                output.write_bytes(b"resampled")
                return None

            with (
                patch.object(
                    ensure_2k,
                    "dimensions",
                    side_effect=[(1280, 720), (2048, 1152)],
                ),
                patch.object(ensure_2k, "run", side_effect=fake_run),
            ):
                result = ensure_2k.produce_2k(source, output, False)

            self.assertEqual("lanczos-resample", result["operation"])
            self.assertIn("scale=2048:1152:flags=lanczos", commands[0])
            self.assertEqual(b"resampled", output.read_bytes())

    def test_non_16_by_9_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "square.png"
            source.write_bytes(b"square")

            with patch.object(ensure_2k, "dimensions", return_value=(1024, 1024)):
                with self.assertRaisesRegex(RuntimeError, "不是 16:9"):
                    ensure_2k.produce_2k(
                        source, root / "final-2K.png", False
                    )

    def test_source_must_be_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.png"
            source.write_bytes(b"source")

            with self.assertRaisesRegex(RuntimeError, "不能相同"):
                ensure_2k.produce_2k(source, source, True)

    def test_existing_output_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.png"
            output = root / "final-2K.png"
            source.write_bytes(b"source")
            output.write_bytes(b"existing")

            with self.assertRaisesRegex(RuntimeError, "添加 --force"):
                ensure_2k.produce_2k(source, output, False)


if __name__ == "__main__":
    unittest.main()
