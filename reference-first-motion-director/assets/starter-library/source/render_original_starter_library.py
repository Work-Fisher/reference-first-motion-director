#!/usr/bin/env python3
"""Render the bundled starter library from self-authored vector primitives.

The script uses Pillow for every visible pixel and FFmpeg only for H.264
encoding. It downloads no assets and embeds no third-party screenshots,
logos, footage, images, or project files.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 30
ROOT = Path(__file__).resolve().parents[1]
CLIPS = ROOT / "clips"
PREVIEWS = ROOT / "previews"
INDEX = ROOT / "_library" / "reference-index.jsonl"
MANIFEST = ROOT / "manifest.json"

RGB = tuple[int, int, int]
FrameRenderer = Callable[[float], Image.Image]


@dataclass(frozen=True)
class Case:
    slug: str
    title: str
    pattern: str
    duration: float
    renderer: FrameRenderer
    summary: str
    motion: str
    palette: str
    tags: list[str]
    roles: list[str]
    segments: list[str]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def ease_out(value: float) -> float:
    return 1.0 - (1.0 - clamp(value)) ** 3


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def mix(a: RGB, b: RGB, amount: float) -> RGB:
    amount = clamp(amount)
    return tuple(round(lerp(x, y, amount)) for x, y in zip(a, b))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    family = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(family, size)


def text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    value: str,
    size: int,
    fill: RGB,
    *,
    bold: bool = False,
    anchor: str = "la",
    stroke_width: int = 0,
    stroke_fill: RGB | None = None,
) -> None:
    draw.text(
        position,
        value,
        font=font(size, bold),
        fill=fill,
        anchor=anchor,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: RGB, width: int = 1) -> None:
    draw.line(points, fill=fill, width=width)


def signal_palette_switch(t: float) -> Image.Image:
    backgrounds = [(9, 17, 31), (11, 15, 18), (22, 13, 35), (22, 8, 10)]
    accents = [(35, 121, 255), (180, 255, 41), (155, 88, 255), (255, 54, 45)]
    labels = ["COLD", "PULSE", "VOLT", "ALERT"]
    state = min(3, int(t / 1.05))
    local = t - state * 1.05
    reveal = smooth(local / 0.18)
    previous = max(0, state - 1)
    bg = mix(backgrounds[previous], backgrounds[state], reveal if state else 1)
    accent = mix(accents[previous], accents[state], reveal if state else 1)
    image = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(image)
    white = (242, 246, 250)
    muted = mix(bg, white, 0.28)

    # Fixed editorial composition: only the active colour state changes.
    for x in range(80, 900, 82):
        line(draw, [(x, 92), (x, 630)], mix(bg, white, 0.07))
    for y in range(92, 631, 72):
        line(draw, [(80, y), (900, y)], mix(bg, white, 0.07))

    text(draw, (82, 70), "SIGNAL STUDY / 01", 18, muted, bold=True)
    text(draw, (82, 232), "COLOUR", 88, white, bold=True)
    text(draw, (82, 330), "BEHAVES", 88, white, bold=True)
    draw.rectangle((87, 385, 628, 397), fill=accent)
    text(draw, (82, 452), "ONE COMPOSITION", 22, muted, bold=True)
    text(draw, (82, 486), "FOUR CONTROLLED STATES", 22, muted, bold=True)

    cx, cy = 758, 274
    draw.ellipse((cx - 118, cy - 118, cx + 118, cy + 118), outline=muted, width=2)
    draw.ellipse((cx - 76, cy - 76, cx + 76, cy + 76), outline=accent, width=13)
    draw.rectangle((cx - 10, cy - 154, cx + 10, cy + 154), fill=accent)
    draw.rectangle((cx - 154, cy - 10, cx + 154, cy + 10), fill=accent)
    draw.ellipse((cx - 25, cy - 25, cx + 25, cy + 25), fill=white)

    panel = (950, 58, 1218, 662)
    draw.rectangle(panel, fill=mix(bg, white, 0.045), outline=mix(bg, white, 0.17), width=2)
    text(draw, (982, 96), "STATE INDEX", 16, muted, bold=True)
    for index, (colour, label) in enumerate(zip(accents, labels)):
        y = 160 + index * 108
        active = index == state
        draw.rectangle((982, y, 1042, y + 60), fill=colour)
        if active:
            draw.rectangle((970, y - 12, 1188, y + 72), outline=white, width=3)
        text(draw, (1070, y + 18), f"0{index + 1}", 16, white if active else muted, bold=True)
        text(draw, (1070, y + 44), label, 14, white if active else muted, bold=True)
    text(draw, (982, 620), f"PHASE 0{state + 1}", 16, accent, bold=True)

    # New-state diagonal shutter establishes the match cut without importing imagery.
    if state and local < 0.22:
        sweep = ease_out(local / 0.22)
        x = lerp(-520, 1500, sweep)
        draw.polygon([(x - 260, 0), (x + 20, 0), (x - 260, HEIGHT), (x - 540, HEIGHT)], fill=accent)
    return image


def modular_assembly_sequence(t: float) -> Image.Image:
    ink = (7, 10, 15)
    paper = (239, 243, 247)
    cobalt = (42, 92, 255)
    cyan = (46, 222, 235)
    acid = (191, 255, 56)
    image = Image.new("RGB", (WIDTH, HEIGHT), ink)
    draw = ImageDraw.Draw(image)
    muted = (86, 95, 110)

    text(draw, (58, 46), "MODULAR ASSEMBLY", 16, (188, 195, 207), bold=True)
    text(draw, (1220, 46), "M03 / ORIGINAL VECTOR STUDY", 14, muted, anchor="ra")
    for x in range(58, 1221, 58):
        line(draw, [(x, 76), (x, 674)], (20, 26, 34))
    for y in range(76, 675, 46):
        line(draw, [(58, y), (1220, y)], (20, 26, 34))

    flash = 4.62 <= t <= 4.78
    final = smooth((t - 4.72) / 0.4)
    if flash:
        return Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))

    canvas_scale = lerp(1.0, 1.08, final)
    canvas_w, canvas_h = 760 * canvas_scale, 500 * canvas_scale
    cx, cy = lerp(512, 640, final), 374
    x0, y0 = cx - canvas_w / 2, cy - canvas_h / 2
    x1, y1 = cx + canvas_w / 2, cy + canvas_h / 2
    draw.rectangle((x0, y0, x1, y1), fill=paper)

    # Modules arrive from independent directions and lock into one poster system.
    arrivals = [0.35, 1.0, 1.65, 2.3, 2.95]
    progress = [ease_out((t - start) / 0.55) for start in arrivals]
    p0, p1, p2, p3, p4 = progress
    left, top = x0 + 56, y0 + 46

    bar_y = lerp(y0 - 70, top, p0)
    draw.rectangle((left, bar_y, x1 - 56, bar_y + 15), fill=cobalt)
    text(draw, (left, bar_y + 32), "SYSTEM / MODULES", 14, ink, bold=True)

    number_x = lerp(x0 - 250, left, p1)
    text(draw, (number_x, top + 88), "72", 152, ink, bold=True)
    draw.rectangle((number_x + 14, top + 252, number_x + 234, top + 268), fill=acid)

    block_x = lerp(x1 + 250, left + 308, p2)
    draw.rectangle((block_x, top + 70, block_x + 332, top + 268), fill=cobalt)
    draw.ellipse((block_x + 74, top + 102, block_x + 230, top + 258), fill=cyan)
    draw.ellipse((block_x + 119, top + 147, block_x + 185, top + 213), fill=ink)

    rules_y = lerp(y1 + 160, top + 322, p3)
    for index, width in enumerate((580, 470, 540)):
        draw.rectangle((left, rules_y + index * 30, left + width, rules_y + index * 30 + 9), fill=ink)

    tag_x = lerp(x1 + 160, x1 - 202, p4)
    draw.rectangle((tag_x, y1 - 93, tag_x + 146, y1 - 47), fill=ink)
    text(draw, (tag_x + 73, y1 - 70), "LOCKED", 14, paper, bold=True, anchor="mm")

    if not final:
        for index, progress_value in enumerate(progress):
            y = 136 + index * 78
            draw.rectangle((1018, y, 1196, y + 52), outline=(60, 70, 84), width=2)
            if progress_value > 0:
                draw.rectangle((1018, y, 1018 + 178 * progress_value, y + 52), fill=(25, 34, 46))
            text(draw, (1040, y + 26), f"MODULE 0{index + 1}", 13, (210, 216, 226), bold=True, anchor="lm")
        text(draw, (1018, 574), "ASSEMBLY PROGRESS", 13, muted, bold=True)
        draw.rectangle((1018, 604, 1196, 612), fill=(32, 40, 52))
        draw.rectangle((1018, 604, 1018 + 178 * (sum(progress) / 5), 612), fill=cyan)
    return image


def editorial_section_stack(t: float) -> Image.Image:
    bg = (6, 8, 12)
    white = (245, 247, 250)
    grey = (71, 78, 91)
    cobalt = (52, 100, 255)
    image = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(image)

    grid = smooth(t / 0.7)
    for x in (78, 284, 490, 696, 902, 1108, 1202):
        line(draw, [(x, 72), (x, lerp(72, 650, grid))], grey)
    line(draw, [(78, 72), (lerp(78, 1202, grid), 72)], grey)
    line(draw, [(78, 650), (lerp(78, 1202, grid), 650)], grey)

    number_p = ease_out((t - 0.35) / 0.55)
    text(draw, (lerp(-180, 78, number_p), 96), "03", 174, cobalt, bold=True)
    text(draw, (1188, 104), "SECTION / STRUCTURE", 15, (150, 157, 170), bold=True, anchor="ra")

    words = [("FORM", 248, 0.85), ("RHYTHM", 362, 1.25), ("SYSTEM", 476, 1.65)]
    for index, (value, y, start) in enumerate(words):
        enter = ease_out((t - start) / 0.52)
        fill_in = smooth((t - (start + 0.38)) / 0.38)
        x = lerp(1280 + index * 90, 286, enter)
        outline_colour = mix(bg, white, 0.37)
        fill_colour = mix(bg, white, fill_in)
        text(
            draw,
            (x, y),
            value,
            102,
            fill_colour,
            bold=True,
            stroke_width=1,
            stroke_fill=outline_colour,
        )
        rule = smooth((t - (start + 0.22)) / 0.42)
        draw.rectangle((288, y + 87, lerp(288, 1110 - index * 74, rule), y + 92), fill=cobalt if index == 1 else grey)

    lock = ease_out((t - 2.45) / 0.45)
    draw.rectangle((lerp(1202, 1020, lock), 585, 1202, 625), fill=cobalt)
    text(draw, (1111, 605), "READ / HOLD", 13, white, bold=True, anchor="mm")
    text(draw, (78, 680), "GUIDES → OUTLINE → SOLID → LOCK", 14, (121, 128, 141), bold=True)
    return image


def kinetic_title_lockup(t: float) -> Image.Image:
    white = (245, 247, 250)
    black = (5, 7, 10)
    cobalt = (43, 93, 255)
    acid = (192, 255, 52)
    image = Image.new("RGB", (WIDTH, HEIGHT), white)
    draw = ImageDraw.Draw(image)

    # Three beat-locked shutters create impact through scale and occlusion.
    intro = ease_out(t / 0.32)
    draw.rectangle((0, 0, lerp(0, 1280, intro), 720), fill=black)
    slash = ease_out((t - 0.28) / 0.4)
    draw.polygon(
        [(lerp(-520, 260, slash), 0), (lerp(-180, 600, slash), 0), (lerp(-520, 260, slash), 720), (lerp(-860, -80, slash), 720)],
        fill=cobalt,
    )

    cut_p = ease_out((t - 0.48) / 0.34)
    with_p = ease_out((t - 0.83) / 0.34)
    intent_p = ease_out((t - 1.18) / 0.4)
    text(draw, (lerp(1380, 110, cut_p), 176), "CUT", 154, white, bold=True)
    text(draw, (lerp(-620, 114, with_p), 332), "WITH", 154, white, bold=True)
    text(draw, (lerp(1480, 110, intent_p), 488), "INTENT", 154, white, bold=True)

    accent_p = smooth((t - 1.58) / 0.34)
    draw.rectangle((112, 622, lerp(112, 910, accent_p), 638), fill=acid)
    badge_p = ease_out((t - 1.82) / 0.32)
    bx = lerp(1280, 1006, badge_p)
    draw.rectangle((bx, 88, bx + 172, 172), fill=white)
    text(draw, (bx + 86, 130), "M10", 31, black, bold=True, anchor="mm")
    text(draw, (1178, 650), "KINETIC LOCKUP", 15, (150, 159, 173), bold=True, anchor="ra")

    # Final micro-hit briefly inverts the title system, then returns to the lockup.
    if 2.48 <= t < 2.58:
        inverted = Image.new("RGB", (WIDTH, HEIGHT), acid)
        inv = ImageDraw.Draw(inverted)
        text(inv, (640, 360), "HOLD", 210, black, bold=True, anchor="mm")
        return inverted
    return image


CASES = [
    Case(
        slug="signal-palette-switch",
        title="信号配色状态切换",
        pattern="M02",
        duration=4.2,
        renderer=signal_palette_switch,
        summary="在完全固定的编辑式构图中切换四个单色状态，用光闸和索引游标把配色变化变成清楚的节拍。",
        motion="构图、尺度和信息位置不动；状态索引依次锁定，斜向色闸在每次换色前快速扫过，最后保留稳定阅读帧。",
        palette="深色底保持统一，只允许钴蓝、酸绿、紫电和警示红依次成为唯一强调色；同一帧不堆叠多组强调色。",
        tags=["配色切换", "固定构图", "单变量", "状态索引", "斜向色闸", "编辑式构图"],
        roles=["P", "C", "M"],
        segments=["00:00.000-00:01.050 冷蓝状态", "00:01.050-00:02.100 酸绿状态", "00:02.100-00:03.150 紫电状态", "00:03.150-00:04.200 警示红状态与停留"],
    ),
    Case(
        slug="modular-assembly-sequence",
        title="模块化构图组装",
        pattern="M03",
        duration=5.8,
        renderer=modular_assembly_sequence,
        summary="五个纯矢量模块从不同方向进入网格、逐项锁定，经一次白闪后收束成完整编辑式海报。",
        motion="空网格先建立；标题条、数字、几何核心、信息规则和状态标签依次到位，进度轨同步增长，白闪后整体放大为完成态。",
        palette="煤黑工作底压住过程信息，冷白画布承载结果，钴蓝为结构主色，青色与酸绿各只承担一个功能节点。",
        tags=["模块组装", "过程展示", "网格", "纯矢量", "白闪", "完成态", "前后状态"],
        roles=["C", "M"],
        segments=["00:00.000-00:00.350 空网格", "00:00.350-00:03.500 五个模块依次锁定", "00:03.500-00:04.620 进度完成与停顿", "00:04.620-00:05.800 白闪和完成态"],
    ),
    Case(
        slug="editorial-section-stack",
        title="编辑式章节标题栈",
        pattern="M05",
        duration=3.8,
        renderer=editorial_section_stack,
        summary="章节编号、导线和三层大字按阅读顺序建立，从低对比描边态转为高对比实字并锁定。",
        motion="导线纵向展开，编号先落位；三层标题错时滑入并从描边转为实字，横向规则随后生长，状态块最后钉住构图。",
        palette="近黑背景与冷灰导线构成结构层，纯白大字负责阅读，钴蓝只用于章节编号、中层规则与最终锁定块。",
        tags=["章节标题", "文字组合", "导线", "描边转实字", "三层结构", "阅读顺序", "钴蓝强调"],
        roles=["C", "M"],
        segments=["00:00.000-00:00.850 导线与章节编号", "00:00.850-00:02.250 三层文字依次显影", "00:02.250-00:03.800 规则生长与锁定停留"],
    ),
    Case(
        slug="kinetic-title-lockup",
        title="节拍式标题钉合",
        pattern="M10",
        duration=3.2,
        renderer=kinetic_title_lockup,
        summary="用三次方向相反的大字入场、一次酸绿规则线和一次短促反相制造标题冲击，结尾回到稳定钉合。",
        motion="黑色满屏与钴蓝斜切先建立能量，三行标题逐拍对撞进入，规则线横向生长，编号徽章锁定后以单次反相完成微击。",
        palette="冷白和煤黑承担主体反差，钴蓝形成斜向动势，酸绿只在规则线与单帧反相中出现。",
        tags=["动势标题", "节拍", "方向对撞", "斜切", "高反差", "编号徽章", "短促反相"],
        roles=["C", "M"],
        segments=["00:00.000-00:00.480 黑场和蓝色斜切", "00:00.480-00:01.580 三层标题逐拍进入", "00:01.580-00:02.480 规则线与徽章钉合", "00:02.480-00:03.200 反相微击与完成态"],
    ),
]


def render_video(case: Case, output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to encode the starter MP4 files.")
    frames = round(case.duration * FPS)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-map_metadata",
        "-1",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_number in range(frames):
            frame = case.renderer(frame_number / FPS).convert("RGB")
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while rendering {case.slug}")


def render_contact_sheet(case: Case, output: Path) -> None:
    columns, rows = 4, 3
    cell_width, cell_height = 320, 180
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (0, 0, 0))
    for index in range(columns * rows):
        time = case.duration * index / (columns * rows - 1)
        frame = case.renderer(time).resize((cell_width, cell_height), Image.Resampling.LANCZOS)
        sheet.paste(frame, ((index % columns) * cell_width, (index // columns) * cell_height))
    sheet.save(output, quality=91, subsampling=0, optimize=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_metadata() -> None:
    records = []
    assets = []
    for case in CASES:
        clip = CLIPS / f"{case.slug}.mp4"
        preview = PREVIEWS / f"{case.slug}.jpg"
        digest = sha256(clip)
        asset_id = digest[:12]
        records.append(
            {
                "aliases": [],
                "distribution": "bundled",
                "duration_seconds": case.duration,
                "extension": ".mp4",
                "fps": float(FPS),
                "height": HEIGHT,
                "id": asset_id,
                "kind": "video",
                "modified_utc": "2026-08-27T00:00:00+00:00",
                "motion": case.motion,
                "palette": case.palette,
                "path": f"clips/{case.slug}.mp4",
                "pattern": case.pattern,
                "preview_frames": 12,
                "preview_path": f"previews/{case.slug}.jpg",
                "reviewed": True,
                "roles": case.roles,
                "segments": case.segments,
                "sha256": digest,
                "size_bytes": clip.stat().st_size,
                "source_type": "self-authored-deterministic-vector-render",
                "summary": case.summary,
                "tags": case.tags,
                "width": WIDTH,
            }
        )
        assets.append(
            {
                "id": asset_id,
                "title": case.title,
                "pattern": case.pattern,
                "clip": f"clips/{case.slug}.mp4",
                "preview": f"previews/{case.slug}.jpg",
                "provenance": "由随包 Python 源码以纯矢量图元逐帧确定性渲染；未使用外部图片、视频、网页截图、Logo 或第三方项目文件。",
            }
        )

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "library_id": "reference-first-motion-director-starter",
        "library_version": "2.0.0",
        "asset_count": len(assets),
        "description": "随 Skill 分发的轻量原创动态参考库；无需配置个人路径即可检索和预览。",
        "render_source": "source/render_original_starter_library.py",
        "packaging_policy": {
            "included": "由仓库内可复现源码绘制的几何图形、排版、色彩和运动帧，以及由这些帧编码的 MP4 与联络表。",
            "excluded": [
                "其他博主、网站或课程的图片、视频、页面截图与工程资产",
                "个人参考库、原始参考 GIF、字幕、逐秒拆帧与第三方品牌素材",
                "对外部案例的逐帧复刻、镜头描摹或可识别布局复制",
                "工具、字体文件、缓存、依赖、可执行文件与实验输出",
            ],
            "use_boundary": "案例只用于学习信息关系、注意力顺序、色彩行为和运动机制；不要把它们当成固定模板或外部案例替代品。",
        },
        "assets": assets,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    CLIPS.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        clip = CLIPS / f"{case.slug}.mp4"
        preview = PREVIEWS / f"{case.slug}.jpg"
        print(f"Rendering {case.pattern}: {case.title}")
        render_video(case, clip)
        render_contact_sheet(case, preview)
    write_metadata()
    print(f"Rendered {len(CASES)} original starter cases into {ROOT}")


if __name__ == "__main__":
    main()
