# Public asset provenance

本仓库只公开能够说明来源与再分发边界的视觉资产。

| 路径 | 来源 | 公开边界 |
|---|---|---|
| `reference-first-motion-director/assets/library-preview/library-cover.svg` | 为本仓库独立绘制的纯 SVG 封面 | 可随仓库在 MIT License 下使用 |
| `reference-first-motion-director/assets/starter-library/source/render_original_starter_library.py` | 为本仓库编写的确定性矢量渲染源码 | 只调用 Pillow 图元与 FFmpeg 编码，不下载或嵌入外部视觉资产 |
| `reference-first-motion-director/assets/starter-library/clips/*.mp4` | 上述源码逐帧绘制并编码的 4 支原创案例 | 可用于学习 M02、M03、M05、M10 的信息关系和运动机制 |
| `reference-first-motion-director/assets/starter-library/previews/*.jpg` | 上述源码从同一帧函数生成的 12 帧联络表 | 与对应 MP4 使用相同边界 |

四支案例的画面只包含脚本绘制的矩形、线条、圆形、纯色和通用演示文字；不包含外部图片、视频、网页截图、Logo、品牌物料或第三方工程文件。仓库也不公开个人参考库、其他博主素材、网页收藏、原始参考 GIF、字幕、拆帧和精确镜头复刻。个人设备能够下载或预览某项内容，不代表获得公开再分发许可。
