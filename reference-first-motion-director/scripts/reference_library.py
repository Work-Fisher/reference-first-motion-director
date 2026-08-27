#!/usr/bin/env python3
"""Maintain the reference inbox and report the primary motion-learning source."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CONFIG_FILENAME = "reference-first-motion-director.json"
SKILL_ROOT = Path(__file__).resolve().parents[1]
STARTER_LIBRARY_RELATIVE = Path("assets") / "starter-library"
CREATOR_LIBRARY_RELATIVE = Path("assets") / "creator-reference-library"
MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
    ".m4v",
}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
}
ANNOTATION_FIELDS = (
    "summary",
    "tags",
    "palette",
    "motion",
    "roles",
    "segments",
    "reviewed",
)


def config_path(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get("MOTION_DIRECTOR_CONFIG")
    if raw:
        return Path(raw).expanduser()
    data_home = os.environ.get("VIDEO_STUDIO_HELPER_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".video-studio-helper"
    return base / CONFIG_FILENAME


def read_config(explicit: str | None = None) -> dict[str, Any]:
    path = config_path(explicit)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"本地配置无法读取: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"本地配置必须是 JSON 对象: {path}")
    return payload


def configured_root(
    explicit: str | None,
    environment_name: str,
    config_key: str,
    config_file: str | None = None,
) -> Path:
    payload = read_config(config_file)
    raw = explicit or os.environ.get(environment_name) or payload.get(config_key)
    if not raw:
        raise ValueError(
            f"尚未配置 {config_key}；请设置 {environment_name}，"
            "或先运行 reference_library.py configure"
        )
    return Path(str(raw)).expanduser()


def optional_configured_root(
    explicit: str | None,
    environment_name: str,
    config_key: str,
    config_file: str | None = None,
) -> Path | None:
    payload = read_config(config_file)
    raw = explicit or os.environ.get(environment_name) or payload.get(config_key)
    return Path(str(raw)).expanduser() if raw else None


def library_root(explicit: str | None = None, config_file: str | None = None) -> Path:
    return configured_root(
        explicit,
        "MOTION_REFERENCE_LIBRARY",
        "reference_library",
        config_file,
    )


def learning_root(explicit: str | None = None, config_file: str | None = None) -> Path:
    return configured_root(
        explicit,
        "MOTION_LEARNING_ROOT",
        "learning_root",
        config_file,
    )


def optional_library_root(
    explicit: str | None = None, config_file: str | None = None
) -> Path | None:
    return optional_configured_root(
        explicit,
        "MOTION_REFERENCE_LIBRARY",
        "reference_library",
        config_file,
    )


def optional_learning_root(
    explicit: str | None = None, config_file: str | None = None
) -> Path | None:
    return optional_configured_root(
        explicit,
        "MOTION_LEARNING_ROOT",
        "learning_root",
        config_file,
    )


def starter_root() -> Path:
    return SKILL_ROOT / STARTER_LIBRARY_RELATIVE


def creator_root() -> Path:
    return SKILL_ROOT / CREATOR_LIBRARY_RELATIVE


def bundled_roots() -> set[Path]:
    return {starter_root().resolve(), creator_root().resolve()}


def write_config(
    reference_library: str,
    primary_learning_root: str,
    explicit: str | None = None,
) -> Path:
    destination = config_path(explicit)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "reference_library": str(Path(reference_library).expanduser().resolve()),
        "learning_root": str(Path(primary_learning_root).expanduser().resolve()),
    }
    handle, temp_name = tempfile.mkstemp(
        prefix="motion-director-config-", suffix=".json", dir=destination.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return destination


def metadata_dir(root: Path) -> Path:
    return root / "_library"


def index_path(root: Path) -> Path:
    return metadata_dir(root) / "reference-index.jsonl"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            denominator_value = float(denominator)
            return float(numerator) / denominator_value if denominator_value else None
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def probe_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,width,height,avg_frame_rate,duration:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return {}

    streams = payload.get("streams") or []
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"), {}
    )
    duration_value = video_stream.get("duration") or (payload.get("format") or {}).get(
        "duration"
    )
    try:
        duration = round(float(duration_value), 3) if duration_value else None
    except (TypeError, ValueError):
        duration = None
    fps = parse_rate(video_stream.get("avg_frame_rate"))
    return {
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "duration_seconds": duration,
        "fps": round(fps, 3) if fps else None,
    }


def read_index(root: Path) -> list[dict[str, Any]]:
    path = index_path(root)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"索引第 {line_number} 行不是有效 JSON: {error}") from error
    return records


def write_index(root: Path, records: Iterable[dict[str, Any]]) -> None:
    destination = index_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix="reference-index-", suffix=".jsonl", dir=destination.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def iter_media(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if "_library" in relative_parts:
            continue
        yield path


def blank_annotations() -> dict[str, Any]:
    return {
        "summary": "",
        "tags": [],
        "palette": "",
        "motion": "",
        "roles": [],
        "segments": [],
        "reviewed": False,
    }


def build_index(root: Path) -> list[dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    previous = {record.get("sha256"): record for record in read_index(root)}
    records_by_digest: dict[str, dict[str, Any]] = {}

    for path in iter_media(root):
        digest = sha256_file(path)
        relative = path.relative_to(root).as_posix()
        existing = records_by_digest.get(digest)
        if existing is not None:
            if relative != existing["path"] and relative not in existing["aliases"]:
                existing["aliases"].append(relative)
            continue

        suffix = path.suffix.lower()
        media_probe = probe_media(path)
        annotations = blank_annotations()
        old_record = previous.get(digest) or {}
        for field in ANNOTATION_FIELDS:
            if field in old_record:
                annotations[field] = old_record[field]

        is_image = suffix in IMAGE_EXTENSIONS
        record = {
            "id": digest[:12],
            "sha256": digest,
            "path": relative,
            "aliases": [],
            "kind": "image" if is_image else "video",
            "extension": suffix,
            "size_bytes": path.stat().st_size,
            "modified_utc": utc_mtime(path),
            "width": media_probe.get("width"),
            "height": media_probe.get("height"),
            "duration_seconds": None if is_image else media_probe.get("duration_seconds"),
            "fps": None if is_image else media_probe.get("fps"),
            **annotations,
        }
        records_by_digest[digest] = record

    records = sorted(records_by_digest.values(), key=lambda record: record["path"].casefold())
    write_index(root, records)
    return records


def find_record(records: Iterable[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    matches = [record for record in records if record.get("id", "").startswith(asset_id)]
    if not matches:
        raise KeyError(f"找不到参考 ID: {asset_id}")
    if len(matches) > 1:
        raise KeyError(f"ID 前缀不唯一，请输入更多字符: {asset_id}")
    return matches[0]


def split_values(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [part.strip() for part in re.split(r"[,，;；]", value) if part.strip()]


def annotate_record(
    root: Path, asset_id: str, values: dict[str, Any]
) -> dict[str, Any]:
    records = read_index(root) or build_index(root)
    target = find_record(records, asset_id)
    for field, value in values.items():
        if value is not None:
            target[field] = value
    target["reviewed"] = True
    write_index(root, records)
    return target


def add_file(root: Path, source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"素材不存在: {source}")
    if source.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError(f"不支持的媒体格式: {source.suffix}")

    root.mkdir(parents=True, exist_ok=True)
    records = build_index(root)
    digest = sha256_file(source)
    duplicate = next((record for record in records if record["sha256"] == digest), None)
    if duplicate:
        return {
            "status": "deduplicated",
            "asset": duplicate,
            "source_preserved": str(source),
        }

    destination = root / source.name
    version = 2
    while destination.exists():
        if sha256_file(destination) == digest:
            records = build_index(root)
            duplicate = next(record for record in records if record["sha256"] == digest)
            return {
                "status": "deduplicated",
                "asset": duplicate,
                "source_preserved": str(source),
            }
        destination = root / f"{source.stem}__v{version}{source.suffix}"
        version += 1

    shutil.copy2(source, destination)
    records = build_index(root)
    added = next(record for record in records if record["sha256"] == digest)
    return {
        "status": "copied",
        "destination": str(destination),
        "asset": added,
        "source_preserved": str(source),
    }


def search_records(
    records: Iterable[dict[str, Any]], query: str | None, unreviewed: bool
) -> list[dict[str, Any]]:
    tokens = [token.casefold() for token in re.split(r"[\s,，;；]+", query or "") if token]
    results: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        if unreviewed and record.get("reviewed"):
            continue
        haystack = json.dumps(record, ensure_ascii=False).casefold()
        score = sum(haystack.count(token) for token in tokens)
        if tokens and score == 0:
            continue
        results.append((score, record))
    results.sort(key=lambda item: (-item[0], item[1]["path"].casefold()))
    return [record for _, record in results]


def sourced_records(root: Path, library: str, build_missing: bool = False) -> list[dict[str, Any]]:
    records = read_index(root)
    if not records and build_missing and root.is_dir():
        records = build_index(root)
    sourced: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item["library"] = library
        item["_library_root"] = str(root.resolve())
        sourced.append(item)
    return sourced


def combined_records(personal_root: Path | None = None) -> list[dict[str, Any]]:
    starter_library = starter_root().resolve()
    creator_library = creator_root().resolve()
    starter = sourced_records(starter_library, "starter")
    creator = sourced_records(creator_library, "creator")
    if not starter:
        raise RuntimeError(f"内置 starter library 缺少索引或素材: {starter_library}")
    if not creator:
        raise RuntimeError(f"内置 creator library 缺少索引或素材: {creator_library}")

    candidates: list[dict[str, Any]] = []
    if personal_root is not None and personal_root.resolve() not in bundled_roots():
        candidates.extend(
            sourced_records(personal_root.resolve(), "personal", build_missing=True)
        )
    candidates.extend(creator)
    candidates.extend(starter)

    records: list[dict[str, Any]] = []
    seen_digests: set[str] = set()
    for record in candidates:
        digests = {
            str(value)
            for value in (record.get("sha256"), record.get("source_sha256"))
            if value
        }
        if digests & seen_digests:
            continue
        seen_digests.update(digests)
        records.append(record)
    return records


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def create_preview(root: Path, record: dict[str, Any], frames: int) -> dict[str, Any]:
    source = root / record["path"]
    if record["kind"] == "image":
        return {
            "library": record.get("library"),
            "kind": "image",
            "source": str(source.resolve()),
        }

    bundled_preview = record.get("preview_path")
    if bundled_preview:
        preview = root / str(bundled_preview)
        if not preview.is_file():
            raise RuntimeError(f"索引中的内置预览不存在: {preview}")
        return {
            "library": record.get("library"),
            "kind": "video-contact-sheet",
            "source": str(source.resolve()),
            "preview": str(preview.resolve()),
            "frames": record.get("preview_frames", 12),
            "prebuilt": True,
        }

    if record.get("library") in {"starter", "creator"}:
        raise RuntimeError("内置素材缺少随包预览，不能写入只读随包库")

    frames = max(4, min(frames, 30))
    duration = record.get("duration_seconds")
    if not duration:
        duration = probe_media(source).get("duration_seconds")
    if not duration:
        raise RuntimeError("无法读取视频时长，不能生成均匀取样预览")

    columns = math.ceil(math.sqrt(frames * 16 / 9))
    rows = math.ceil(frames / columns)
    output_dir = metadata_dir(root) / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{record['id']}_{frames}f.jpg"
    sample_rate = frames / max(float(duration), 0.001)
    video_filter = (
        f"fps={sample_rate:.8f},scale=480:-2,"
        f"tile={columns}x{rows}:nb_frames={frames}:padding=4:margin=4"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vf",
        video_filter,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output),
    ]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as error:
        raise RuntimeError("找不到 ffmpeg，无法生成视频预览") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"ffmpeg 生成预览失败: {source.name}") from error
    return {
        "library": record.get("library"),
        "kind": "video-contact-sheet",
        "source": str(source.resolve()),
        "preview": str(output.resolve()),
        "frames": frames,
    }


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "id",
            "library",
            "path",
            "kind",
            "width",
            "height",
            "duration_seconds",
            "summary",
            "tags",
            "palette",
            "motion",
            "roles",
            "segments",
            "pattern",
            "creator",
            "license",
            "source_type",
            "reviewed",
        )
    }


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理动态视觉本地参考库")
    parser.add_argument("--config", help="覆盖本地路径配置文件")
    parser.add_argument("--root", help="覆盖参考库根目录")
    parser.add_argument("--learning-root", help="覆盖主剪辑学习知识库根目录")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure_parser = subparsers.add_parser("configure", help="保存本机素材库路径")
    configure_parser.add_argument("--reference-library", required=True)
    configure_parser.add_argument("--primary-learning-root", required=True)

    subparsers.add_parser("status", help="检查主知识库与新参考入口状态")
    subparsers.add_parser("index", help="扫描媒体并重建索引")

    search_parser = subparsers.add_parser("search", help="检索参考")
    search_parser.add_argument("--query", default="")
    search_parser.add_argument("--unreviewed", action="store_true")

    show_parser = subparsers.add_parser("show", help="查看一条完整记录")
    show_parser.add_argument("--asset-id", required=True)

    preview_parser = subparsers.add_parser("preview", help="生成或返回预览")
    preview_parser.add_argument("--asset-id", required=True)
    preview_parser.add_argument("--frames", type=int, default=12)

    add_parser = subparsers.add_parser("add", help="复制新参考并自动去重")
    add_parser.add_argument("--file", required=True)

    annotate_parser = subparsers.add_parser("annotate", help="写入人工视觉分析")
    annotate_parser.add_argument("--asset-id", required=True)
    annotate_parser.add_argument("--summary")
    annotate_parser.add_argument("--tags")
    annotate_parser.add_argument("--palette")
    annotate_parser.add_argument("--motion")
    annotate_parser.add_argument("--roles")
    annotate_parser.add_argument("--segments")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.command == "configure":
            destination = write_config(
                args.reference_library,
                args.primary_learning_root,
                args.config,
            )
            print_json(
                {
                    "config": str(destination.resolve()),
                    "reference_library": str(
                        library_root(config_file=args.config).resolve()
                    ),
                    "learning_root": str(
                        learning_root(config_file=args.config).resolve()
                    ),
                }
            )
            return 0

        personal = optional_library_root(args.root, args.config)
        if personal is not None:
            personal = personal.resolve()
        primary = optional_learning_root(args.learning_root, args.config)
        if primary is not None:
            primary = primary.resolve()
        if args.command == "status":
            learning_docs = (
                primary / "Seedream5_剪辑拆解" / "学习资料" if primary else None
            )
            contact_sheets = (
                primary
                / "Seedream5_剪辑拆解"
                / "derived"
                / "vibe_motion_gif_analysis"
                if primary
                else None
            )
            bundled_root = starter_root().resolve()
            bundled_records = read_index(bundled_root)
            creator_library = creator_root().resolve()
            creator_records = read_index(creator_library)
            personal_records = read_index(personal) if personal else []
            print_json(
                {
                    "ready_to_search": bool(bundled_records and creator_records),
                    "starter_library": str(bundled_root),
                    "starter_exists": bundled_root.is_dir(),
                    "indexed_starter_assets": len(bundled_records),
                    "creator_library": str(creator_library),
                    "creator_exists": creator_library.is_dir(),
                    "indexed_creator_assets": len(creator_records),
                    "primary_learning_root": str(primary) if primary else None,
                    "primary_exists": primary.is_dir() if primary else False,
                    "root_index_exists": (primary / "data_structure.md").is_file()
                    if primary
                    else False,
                    "source_gifs": len(list((primary / "GIF").glob("*.webp")))
                    if primary
                    else 0,
                    "learning_documents": len(list(learning_docs.glob("*")))
                    if learning_docs and learning_docs.is_dir()
                    else 0,
                    "gif_contact_sheets": len(list(contact_sheets.glob("*_contact_sheet.jpg")))
                    if contact_sheets and contact_sheets.is_dir()
                    else 0,
                    "reference_inbox": str(personal) if personal else None,
                    "inbox_exists": personal.is_dir() if personal else False,
                    "inbox_index": str(index_path(personal)) if personal else None,
                    "indexed_inbox_assets": len(personal_records),
                    "unreviewed_inbox_assets": sum(
                        not record.get("reviewed", False) for record in personal_records
                    ),
                }
            )
        elif args.command == "index":
            root = library_root(args.root, args.config).resolve()
            if root in bundled_roots():
                raise ValueError("随包参考库只读，请配置个人参考库后再索引")
            records = build_index(root)
            print_json(
                {
                    "root": str(root),
                    "index": str(index_path(root)),
                    "assets": len(records),
                    "images": sum(record["kind"] == "image" for record in records),
                    "videos": sum(record["kind"] == "video" for record in records),
                    "unreviewed": sum(not record["reviewed"] for record in records),
                }
            )
        elif args.command == "search":
            records = combined_records(personal)
            print_json(
                [
                    compact_record(record)
                    for record in search_records(records, args.query, args.unreviewed)
                ]
            )
        elif args.command == "show":
            records = combined_records(personal)
            print_json(public_record(find_record(records, args.asset_id)))
        elif args.command == "preview":
            records = combined_records(personal)
            record = find_record(records, args.asset_id)
            root = Path(str(record["_library_root"]))
            print_json(create_preview(root, record, args.frames))
        elif args.command == "add":
            root = library_root(args.root, args.config).resolve()
            if root in bundled_roots():
                raise ValueError("随包参考库只读，请配置个人参考库后再添加")
            print_json(add_file(root, Path(args.file)))
        elif args.command == "annotate":
            root = library_root(args.root, args.config).resolve()
            if root in bundled_roots():
                raise ValueError("随包参考库只读，请配置个人参考库后再标注")
            values = {
                "summary": args.summary,
                "tags": split_values(args.tags),
                "palette": args.palette,
                "motion": args.motion,
                "roles": split_values(args.roles),
                "segments": split_values(args.segments),
            }
            print_json(annotate_record(root, args.asset_id, values))
        else:
            raise ValueError(f"未知命令: {args.command}")
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
