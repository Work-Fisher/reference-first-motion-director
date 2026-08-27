#!/usr/bin/env python3
"""Validate a generated image and produce an exact 2048x1152 PNG."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


TARGET_WIDTH = 2048
TARGET_HEIGHT = 1152
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT
RATIO_TOLERANCE = 0.02


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def dimensions(path: Path) -> tuple[int, int]:
    try:
        result = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=s=x:p=0",
                str(path),
            ]
        )
    except FileNotFoundError as error:
        raise RuntimeError("找不到 ffprobe；请先安装 FFmpeg。") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"无法读取图片尺寸：{error.stderr.strip()}") from error

    value = result.stdout.strip()
    try:
        width_text, height_text = value.split("x", maxsplit=1)
        return int(width_text), int(height_text)
    except (ValueError, TypeError) as error:
        raise RuntimeError(f"ffprobe 返回了无法解析的尺寸：{value!r}") from error


def ensure_ratio(width: int, height: int) -> None:
    ratio = width / height
    if abs(ratio - TARGET_RATIO) > RATIO_TOLERANCE:
        raise RuntimeError(
            f"源图为 {width}x{height}，不是 16:9。请先重新生成或有意识地裁切，"
            "不要直接拉伸成 2K。"
        )


def produce_2k(source: Path, output: Path, force: bool) -> dict[str, object]:
    if not source.is_file():
        raise RuntimeError(f"源图不存在：{source}")
    if output.suffix.lower() != ".png":
        raise RuntimeError("最终 2K 文件必须使用 .png 扩展名。")
    if source.resolve() == output.resolve():
        raise RuntimeError("源文件与输出文件不能相同；必须保留原始生成图。")
    if output.exists() and not force:
        raise RuntimeError(f"输出文件已存在：{output}；确认覆盖时添加 --force。")

    source_width, source_height = dimensions(source)
    ensure_ratio(source_width, source_height)
    output.parent.mkdir(parents=True, exist_ok=True)

    if (source_width, source_height) == (TARGET_WIDTH, TARGET_HEIGHT):
        shutil.copy2(source, output)
        operation = "copy"
    else:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if force else "-n",
            "-i",
            str(source),
            "-vf",
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos",
            "-frames:v",
            "1",
            str(output),
        ]
        try:
            run(command)
        except FileNotFoundError as error:
            raise RuntimeError("找不到 ffmpeg；请先安装 FFmpeg。") from error
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"2K 输出失败：{error.stderr.strip()}") from error
        operation = "lanczos-resample"

    final_width, final_height = dimensions(output)
    if (final_width, final_height) != (TARGET_WIDTH, TARGET_HEIGHT):
        raise RuntimeError(
            f"最终尺寸验收失败：得到 {final_width}x{final_height}，"
            f"要求 {TARGET_WIDTH}x{TARGET_HEIGHT}。"
        )

    return {
        "source": str(source.resolve()),
        "source_dimensions": f"{source_width}x{source_height}",
        "output": str(output.resolve()),
        "final_dimensions": f"{final_width}x{final_height}",
        "operation": operation,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 16:9 生成图验收并输出为精确的 2048x1152 PNG。"
    )
    parser.add_argument("source", type=Path, help="原始生成图")
    parser.add_argument("--output", type=Path, required=True, help="最终 *-2K.png 路径")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的明确输出文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = produce_2k(args.source, args.output, args.force)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
