# 个人参考入口协议

本文件只管理个人配置中的增量入口 `<reference-library>`。随包只读基线见 [starter-library.md](starter-library.md) 与 [creator-reference-library.md](creator-reference-library.md)；主知识库 `<learning-root>` 是分层、只读的训练资料，按 [knowledge-map.md](knowledge-map.md) 和其中的 `data_structure.md` 导航。不要把整个主知识库交给本脚本递归索引，否则会把逐秒帧、工具依赖和实验输出误当成同级案例。

## 目录规则

不配置时，`status`、`search`、`show` 和 `preview` 会直接读取 48 项 creator library 与 4 项 starter library。需要增加自己的素材时，通过 `configure` 保存 `reference_library` 和 `learning_root`。配置默认位于 `VIDEO_STUDIO_HELPER_HOME`，未设置时位于用户目录的 `.video-studio-helper/reference-first-motion-director.json`；环境变量 `MOTION_REFERENCE_LIBRARY`、`MOTION_LEARNING_ROOT` 可以临时覆盖。脚本会在个人参考入口创建：

```text
视频参考/
├─ 用户的图片与视频
└─ _library/
   ├─ reference-index.jsonl
   └─ previews/
```

不要把生成稿、测试稿和未确认结果放进这个入口。它只保存用户后来提供或明确认可的新参考，不是普通输出目录。

## 基础命令

从技能目录执行：

```powershell
python -X utf8 scripts/reference_library.py status
python -X utf8 scripts/reference_library.py search --query "黑底 光学 字体"
python -X utf8 scripts/reference_library.py show --asset-id <ID>
python -X utf8 scripts/reference_library.py preview --asset-id <ID> --frames 12
python -X utf8 scripts/reference_library.py configure --reference-library "<reference-library>" --primary-learning-root "<learning-root>"
python -X utf8 scripts/reference_library.py index
python -X utf8 scripts/reference_library.py search --unreviewed
python -X utf8 scripts/reference_library.py add --file "<incoming-reference.mp4>"
```

也可从任意目录用脚本绝对路径运行。检索结果的 `library` 字段会标明 `creator`、`starter` 或 `personal`；个人库与随包库合并检索，原始内容哈希相同时个人记录优先。`index` 会递归扫描个人参考库，但跳过 `_library/`；两个内置库只读，不能对它们执行 `index`、`add` 或 `annotate`。

## 加入附件

1. 先查看附件并判断是否真是视觉参考。
2. 使用 `add` 复制，不移动源文件。
3. 内容哈希相同：返回已有 ID，不产生第二份文件。
4. 同名但内容不同：保存为 `名称__v2.ext`、`名称__v3.ext`。
5. 运行 `preview`；图片返回原图路径，视频生成均匀取样联络表。
6. 使用 `annotate` 完成机制级标注。

```powershell
python -X utf8 scripts/reference_library.py annotate `
  --asset-id <ID> `
  --summary "黑底上的光谱流体与高对比衬线字" `
  --tags "黑底,光谱,折射,字体" `
  --palette "冷青与深紫由折射光产生，后段转红洋红" `
  --motion "色彩像透明液体穿过字面，缓慢迁移" `
  --roles "P,M" `
  --segments "00:00.500 冷青电蓝深紫；00:00.000-00:07.400 光谱迁移"
```

## 元数据含义

- `id`：SHA-256 前 12 位，内容不变则 ID 不变。
- `path`：相对参考库路径。
- `aliases`：库内重复内容的其他相对路径。
- `summary`：这项案例真正值得学习的一句话。
- `tags`：可被检索的主题与视觉机制。
- `palette`：颜色来源、材料和变化方式，不只是色名。
- `motion`：主运动规律、速度和收束。
- `roles`：适合作为 `P`、`C`、`M` 中的哪些角色。
- `segments`：视频关键时间点/时间段，或图片局部说明。
- `reviewed`：是否经过真人或视觉检查，而非仅自动探测。

索引是 JSON Lines（JSONL，逐行 JSON）文件，方便增量检索和 Git 以外的本地使用。

## 检索原则

检索词优先来自“关系 + 机制”，而不是泛泛的“高级感”。例如：

- `规模 重复 字墙`
- `黑底 折射 光谱 字体`
- `真实界面 页面旅程`
- `单核 扩张 关系场`

选中结果后仍要查看源图或精确视频帧。索引摘要只能导航，不能替代观看。整片节奏、人物/证据分配和 M01–M10 模式优先从已配置的主知识库检索；没有主知识库时先读随包机制案例。个人入口的结果补充 P/C/M 视觉候选。

## 权利与来源

只保存用户有权持有或明确提供的参考。保存不等于获得再分发权；只有明确确认原创或持有公开再分发与指定许可证再许可权的素材，才可以经隐私清理后进入 creator 随包库。输出只抽取色彩行为、排版关系、镜头逻辑和运动机制，不复刻 Logo、品牌文案、完整构图或逐帧序列。
