#!/usr/bin/env python3
"""Build a privacy-sanitized, redistributable creator reference library."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = SKILL_ROOT / "assets" / "creator-reference-library"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
PUBLISHED_AT = "2026-08-27T00:00:00+00:00"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def executable(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise RuntimeError(f"Required executable is unavailable: {name}")
    return result


def read_records(source: Path) -> list[dict[str, Any]]:
    index = source / "_library" / "reference-index.jsonl"
    if not index.is_file():
        raise FileNotFoundError(f"Missing source index: {index}")
    records = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line]
    if not records:
        raise ValueError("The source index is empty.")
    return records


def save_still(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as original:
        if getattr(original, "is_animated", False) and output.suffix.lower() == ".gif":
            frames: list[Image.Image] = []
            durations: list[int] = []
            for number in range(original.n_frames):
                original.seek(number)
                frames.append(original.convert("RGBA"))
                durations.append(int(original.info.get("duration", 100)))
            frames[0].save(
                output,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=int(original.info.get("loop", 0)),
                disposal=2,
                optimize=False,
            )
            return
        image = ImageOps.exif_transpose(original)
        suffix = output.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            image.convert("RGB").save(output, quality=95, optimize=True, progressive=True)
        elif suffix == ".png":
            image.save(output, format="PNG", optimize=True)
        elif suffix == ".webp":
            image.save(output, format="WEBP", quality=95, method=6)
        else:
            raise ValueError(f"Unsupported image format: {suffix}")


def save_video(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
        "-map_metadata", "-1", "-map_chapters", "-1", "-c", "copy",
    ]
    if output.suffix.lower() == ".mp4":
        command.extend(["-movflags", "+faststart"])
    subprocess.run([*command, str(output)], check=True)


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            executable("ffprobe"), "-v", "error",
            "-show_entries", "stream=codec_type,width,height,avg_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = next(item for item in payload["streams"] if item.get("codec_type") == "video")
    numerator, denominator = stream.get("avg_frame_rate", "0/1").split("/", 1)
    fps = float(numerator) / float(denominator) if float(denominator) else None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "duration_seconds": round(float(payload["format"]["duration"]), 3),
        "fps": round(fps, 3) if fps else None,
    }


def render_contact_sheet(source: Path, output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    video_filter = (
        f"fps={12 / max(duration, 0.001):.8f},"
        "scale=320:180:force_original_aspect_ratio=decrease,"
        "pad=320:180:(ow-iw)/2:(oh-ih)/2:color=0x080a0e,"
        "tile=4x3:nb_frames=12:padding=4:margin=4"
    )
    subprocess.run(
        [
            executable("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-vf", video_filter, "-frames:v", "1",
            "-q:v", "2", "-map_metadata", "-1", str(output),
        ],
        check=True,
    )


def still_thumbnail(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.seek(0)
        return ImageOps.exif_transpose(image).convert("RGB")


def video_thumbnail(path: Path, duration: float) -> Image.Image:
    result = subprocess.run(
        [
            executable("ffmpeg"), "-hide_banner", "-loglevel", "error",
            "-ss", f"{max(duration * 0.28, 0.01):.3f}", "-i", str(path),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        capture_output=True,
        check=True,
    )
    with Image.open(io.BytesIO(result.stdout)) as image:
        return image.convert("RGB")


def render_overview(output: Path, records: list[dict[str, Any]], root: Path) -> None:
    width, height, columns = 240, 135, 6
    sheet = Image.new("RGB", (width * columns, height * 8), (4, 6, 9))
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
    for index, record in enumerate(records):
        path = root / record["path"]
        thumbnail = (
            video_thumbnail(path, float(record["duration_seconds"]))
            if record["kind"] == "video"
            else still_thumbnail(path)
        )
        fitted = ImageOps.contain(thumbnail, (width, height), Image.Resampling.LANCZOS)
        cell = Image.new("RGB", (width, height), (7, 9, 13))
        cell.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
        x, y = (index % columns) * width, (index // columns) * height
        sheet.paste(cell, (x, y))
        draw.rectangle((x, y + height - 27, x + width, y + height), fill=(4, 6, 9))
        marker = "V" if record["kind"] == "video" else "I"
        draw.text(
            (x + 10, y + height - 21),
            f"{marker}{index + 1:02d}  {record['id']}",
            font=label_font,
            fill=(237, 241, 248),
        )
    sheet.save(output, quality=91, subsampling=0, optimize=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in records) + "\n",
        encoding="utf-8",
    )


def build(source: Path, output: Path, creator: str, version: str, confirmed_on: str) -> None:
    source, output = source.resolve(), output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Build into a clean review directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    published: list[dict[str, Any]] = []

    for position, record in enumerate(read_records(source), start=1):
        source_file = source / record["path"]
        if not record.get("reviewed") or not source_file.is_file():
            raise ValueError(f"Unreviewed or missing source record: {record.get('id')}")
        source_hash = digest(source_file)
        if source_hash != record.get("sha256"):
            raise ValueError(f"Source changed after indexing: {source_file}")
        suffix, kind = source_file.suffix.lower(), record["kind"]
        if kind == "image" and suffix not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image: {source_file}")
        if kind == "video" and suffix not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video: {source_file}")

        folder = output / "media" / ("images" if kind == "image" else "videos")
        temporary = folder / f"source-{position:02d}{suffix}"
        save_still(source_file, temporary) if kind == "image" else save_video(source_file, temporary)
        packaged_hash = digest(temporary)
        asset_id = packaged_hash[:12]
        destination = temporary.with_name(f"{asset_id}{suffix}")
        temporary.replace(destination)

        if kind == "image":
            with Image.open(destination) as image:
                width, height = image.size
            probe = {"width": width, "height": height, "duration_seconds": None, "fps": None}
            preview_path = None
        else:
            probe = probe_video(destination)
            preview = output / "previews" / "videos" / f"{asset_id}_12f.jpg"
            render_contact_sheet(destination, preview, float(probe["duration_seconds"]))
            preview_path = preview.relative_to(output).as_posix()

        published.append(
            {
                "aliases": [],
                "creator": creator,
                "distribution": "bundled-creator",
                "duration_seconds": probe["duration_seconds"],
                "extension": suffix,
                "fps": probe["fps"],
                "height": probe["height"],
                "id": asset_id,
                "kind": kind,
                "license": "CC-BY-NC-4.0",
                "modified_utc": PUBLISHED_AT,
                "motion": record.get("motion", ""),
                "palette": record.get("palette", ""),
                "path": destination.relative_to(output).as_posix(),
                "preview_frames": 12 if preview_path else None,
                "preview_path": preview_path,
                "reviewed": True,
                "rights": f"creator-confirmed-{confirmed_on}",
                "roles": record.get("roles", []),
                "segments": record.get("segments", []),
                "sha256": packaged_hash,
                "size_bytes": destination.stat().st_size,
                "source_id": record["id"],
                "source_sha256": source_hash,
                "source_type": "creator-owned-or-redistribution-authorized",
                "summary": record.get("summary", ""),
                "tags": record.get("tags", []),
                "width": probe["width"],
            }
        )

    published.sort(key=lambda item: (item["kind"], item["id"]))
    write_jsonl(output / "_library" / "reference-index.jsonl", published)
    render_overview(output / "overview.jpg", published, output)
    write_json(
        output / "manifest.json",
        {
            "schema_version": 1,
            "library_id": "reference-first-motion-director-creator-library",
            "library_version": version,
            "creator": creator,
            "license": "CC-BY-NC-4.0",
            "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
            "rights_confirmation": (
                "The repository maintainer confirmed authorship or public redistribution "
                f"and CC BY-NC 4.0 relicensing rights on {confirmed_on}."
            ),
            "asset_count": len(published),
            "image_count": sum(item["kind"] == "image" for item in published),
            "video_count": sum(item["kind"] == "video" for item in published),
            "total_media_bytes": sum(item["size_bytes"] for item in published),
            "privacy_processing": [
                "Published filenames use packaged SHA-256 prefixes.",
                "Image EXIF, XMP, and editor metadata is removed by pixel re-encoding.",
                "Video container metadata and chapters are removed without re-encoding streams.",
                "Local absolute paths and original filenames are excluded.",
            ],
            "index": "_library/reference-index.jsonl",
            "overview": "overview.jpg",
        },
    )
    (output / "LICENSE.md").write_text(
        "# Creator reference library license\n\n"
        f"Copyright © 2026 {creator}.\n\n"
        "The media files, video previews, overview image, and descriptive index in this "
        "directory are licensed under the [Creative Commons Attribution-NonCommercial "
        "4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).\n\n"
        f"Attribution: **{creator} — Reference-first Motion Director creator library**.\n\n"
        "The license applies only to this directory. Skill instructions and source code "
        "remain under the repository's MIT License.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the bundled creator reference library")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--creator", default="Work-Fisher")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--rights-confirmed-on", default="2026-08-27")
    args = parser.parse_args()
    build(Path(args.source), Path(args.output), args.creator, args.version, args.rights_confirmed_on)
    print(f"Built creator reference library: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
