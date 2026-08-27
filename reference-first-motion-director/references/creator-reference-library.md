# 创作者随包参考库

`assets/creator-reference-library/` 是由仓库维护者授权公开分发的扩展参考库。它包含 33 张图片、15 支视频、15 张视频联络表、1 张总览图和 48 条人工机制标注。

## 使用边界

- 媒体、联络表、总览图和描述索引采用 `CC BY-NC 4.0`，署名为 `Work-Fisher — Reference-first Motion Director creator library`。
- Skill 指令、Python 脚本和其他代码继续使用仓库 MIT License。
- 参考库用于选择色彩行为、构图关系和运动机制；生成时仍不得复制其中的 Logo、品牌文案、完整布局或逐帧序列。
- `creator` 是只读随包库；`index`、`add` 和 `annotate` 继续只写个人参考入口。

## 隐私与可移植性

公开副本不保留本机绝对路径和原始文件名。图片通过像素重编码移除 EXIF、XMP 与编辑器元数据；视频在不重编码音视频流的情况下移除容器元数据和章节。文件名使用发布副本 SHA-256 前 12 位。

个人库记录的原始 SHA-256 保存在 `source_sha256`。同一素材同时存在于个人库和随包创作者库时，检索优先返回个人记录并去重。

## 更新流程

先在个人参考库中完成查看、索引和人工标注，再构建到一个干净的审查目录：

```powershell
python -X utf8 scripts/build_creator_library.py `
  --source "<reference-library>" `
  --output "<clean-review-directory>" `
  --creator "Work-Fisher" `
  --version "<next-version>" `
  --rights-confirmed-on "YYYY-MM-DD"
```

逐张查看 `overview.jpg` 和视频联络表，核对 `manifest.json` 的数量、许可证与隐私处理，再把审查目录同步到 `assets/creator-reference-library/`。构建脚本拒绝写入非空目录，避免静默覆盖现有随包库。
