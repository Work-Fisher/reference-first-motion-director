# Public asset provenance

本仓库只公开能够说明来源与再分发边界的视觉资产。

| 路径 | 来源 | 公开边界 |
|---|---|---|
| `reference-first-motion-director/assets/library-preview/library-cover.svg` | 为本仓库独立绘制的纯 SVG 封面 | 可随仓库在 MIT License 下使用 |
| `reference-first-motion-director/assets/starter-library/source/render_original_starter_library.py` | 为本仓库编写的确定性矢量渲染源码 | 只调用 Pillow 图元与 FFmpeg 编码，不下载或嵌入外部视觉资产 |
| `reference-first-motion-director/assets/starter-library/clips/*.mp4` | 上述源码逐帧绘制并编码的 4 支原创案例 | 可用于学习 M02、M03、M05、M10 的信息关系和运动机制 |
| `reference-first-motion-director/assets/starter-library/previews/*.jpg` | 上述源码从同一帧函数生成的 12 帧联络表 | 与对应 MP4 使用相同边界 |
| `reference-first-motion-director/assets/creator-reference-library/**` | Work-Fisher 确认原创或持有公开再分发与 `CC BY-NC 4.0` 再许可权的 48 项媒体；发布副本经隐私清理 | 媒体、预览、总览图和描述索引按目录内 `LICENSE.md` 使用；不得将参考选择误解为复制 Logo、品牌文案、完整布局或逐帧序列的授权 |

四支 starter 案例的画面只包含脚本绘制的矩形、线条、圆形、纯色和通用演示文字。创作者随包库与 starter 分开索引、分开许可；其公开依据为仓库维护者在 2026-08-27 作出的原创或再分发及再许可确认。仓库不公开未授权个人参考库、字幕、拆帧和精确镜头复刻。个人设备能够下载或预览某项内容，不代表获得公开再分发许可。
