# 知识源地图与可信度

## 四层知识源

### 随包 starter library

`assets/starter-library/`，无需配置，所有安装者可直接读取。

它提供 M02、M03、M05、M10 四个轻量动效案例、联络表与人工机制标注，是可移植的最低可用基线。它不替代完整主知识库，也不代表只有这四种表现形态。详见 [starter-library.md](starter-library.md)。

### 创作者随包参考库

`assets/creator-reference-library/`，无需配置，所有安装者可直接读取。

它提供 33 张图片、15 支视频及 48 条人工机制标注，承担具体的色彩、构图、字体、材质和运动候选。媒体由仓库维护者确认拥有公开再分发与 `CC BY-NC 4.0` 再许可权；发布副本已移除本机路径、原始文件名和可移除元数据。详见 [creator-reference-library.md](creator-reference-library.md)。

### 主知识库

`<learning-root>`，由个人配置或 `MOTION_LEARNING_ROOT` 指定。

它决定整片编辑逻辑、运动模式与审美基线。按以下层级使用：

| 级别 | 路径 | 用途 |
|---|---|---|
| T1 原始依据 | `GIF/` | 9 个原始 Vibe Motion 动效，运动语法的最高优先级 |
| T1 实测拆解 | `Seedream5_剪辑拆解/学习资料/` | 14:03 成片的 140 段、843 秒、16 份总结与复刻文档 |
| T1 可视分析 | `Seedream5_剪辑拆解/derived/vibe_motion_gif_analysis/*_contact_sheet.jpg` | 9 个 GIF 的完整状态序列概览 |
| T2 已验证复刻 | `motion-lab/out/` 中 README/package scripts 指向的当前版本 | 用来理解状态机、曲线与可执行实现 |
| T2 实现 | `motion-lab/src/compositions/` | 需要精确理解投影、连续曲线、遮罩或时序时读取 |
| T3 视觉素材池 | `素材收集/` | 色彩、排版、界面、质感与覆盖素材候选；需逐项查看 |
| T4 实验 | `motion-lab/out/*review*`、早期 `v1/v2`、Flova D 系列 | 只提取明确机制，不自动当正面审美标准 |
| 派生导航 | `frames_1fps/`、`derived/*.csv`、分析图 | 用于验证精确秒点，不作为独立案例逐张检索 |
| 非知识 | `.analysis_tools/`、`node_modules/`、`__pycache__/` | 工具依赖，始终跳过 |

“位于主知识库”不等于“每个文件都代表喜欢的审美”。原始 GIF、明确通过版本和学习文档的权重大于实验输出；素材背景、网格、粒子、片尾梗图只在具体任务需要时调用。

### 新参考入口

`<reference-library>`，由个人配置或 `MOTION_REFERENCE_LIBRARY` 指定。

这里负责未来增量。`_library/reference-index.jsonl` 保存哈希、预览和人工标注。它不会覆盖主知识库，只会提供新的 P/C/M 候选。

脚本检索时把个人入口与随包库合并；相同 SHA-256 优先保留个人记录。主知识库继续通过本文件和 `data_structure.md` 分层导航，不递归混入扁平媒体索引。

## 按问题导航

- **整片脚本怎么分配人物/素材/录屏/动效**：先读 `editorial-routing.md`，必要时查询 `01_分段总表.csv`。
- **这段关系应该怎么动**：读 `motion-pattern-library.md`，再看对应 GIF contact sheet 和 09–15 号学习文档。
- **颜色、字体、构图为什么高级**：读 `visual-dna.md`，再查看具体源图/源帧。
- **精确时点、帧率与连续运动**：读对应学习文档、`frame-manifest.csv` 或 motion-lab 源码。
- **没有配置本机素材库**：用 `reference_library.py` 直接检索 48 项创作者参考与 4 项 starter 案例。
- **新参考**：配置个人入口后，用 `reference_library.py` 入库、检索和预览。
- **某个 Motion 模板的实现**：先读 `motion-lab/README.md`，再读对应 `src/compositions/*.tsx`，不遍历整个工程。

## 主知识库中的关键入口

- `学习资料/00_先看这里_学习路线.md`：总体方法与工具路线。
- `学习资料/04_全片结构与剪辑规律.md`：画面职责和脉冲节奏。
- `学习资料/05_动效复刻手册.md`：基础运动与镜头模板。
- `学习资料/08_Vibe_Motion素材核对与路线修正.md`：9 个 GIF 和真实制作路径。
- `学习资料/09–15_*.md`：M03–M08 的精确状态机。
- `motion-lab/README.md`：已实现模式与当前通过版本。

## 更新原则

- 主知识库新增正式拆解或明确通过版本：更新本地图索引与相应机制文档。
- 用户临时发来参考：先进入新参考入口，不随意改主知识体系。
- 用户明确把某个结果判定为正面或失败：记录这个评价，优先于文件名中的 `final/review` 推断。
