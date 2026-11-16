# BugWorld 商店素材

制作日期：2026-11-16。图标经用户确认后成为 1.0.21 正式应用图标；素材与代码同步到 GitHub 功能分支。应用交互逻辑不变。

| 文件 | 规格 | 内容 / 来源 |
| --- | --- | --- |
| BugWorld-AppIcon-1024.png | 1024×1024，1,616,767 字节 | 蝴蝶与绿叶，内置 imagegen 生成；无文字、无预制圆角 |
| BugWorld-Poster-2560x1440.png | 2560×1440，16:9 | 治愈森林主题 AI 宣传插画，非应用实机截图 |
| screenshots/01-Shared-Space.png | 2560×1440，16:9 | 00:00.500，画板与画具 |
| screenshots/02-Finger-Coloring.png | 2560×1440，16:9 | 01:18.000，手指涂色 |
| screenshots/03-3D-Preview.png | 2560×1440，16:9 | 01:55.700，涂色后的 3D 预览 |
| screenshots/04-Forest-Garden.png | 2560×1440，16:9 | 02:27.000，森林花园 |
| screenshots/05-Hand-Interaction.png | 2560×1440，16:9 | 02:38.500，伸手邀请蝴蝶；不表示已完成落掌 |

五张截图来自用户提供的 `BugWorld_ScreenRecording_2026.11.03.mp4`，原视频约 3 分 27 秒、2560×1440。使用 FFmpeg 原尺寸提取 PNG，未 AI 重绘、未裁切、未更改画面内容，保留录像原有 UI。录像日期不代表当前应用版本。时间为提取时指定的 seek 时间，实际画面落在相邻视频帧上。

图标和海报由内置 imagegen 制作，再用 FFmpeg Lanczos 缩放到交付尺寸；海报按 16:9 居中裁切。图标小于 4,000,000 字节；七张 PNG 均经文件解码和像素尺寸检查，并逐张目视复核。

`manifest.json` 记录文件大小、尺寸、SHA-256 与截图时间；`prompts.md` 保存生成提示词。原视频保持不变。

## 1.0.21 正式图标接入

- `scripts/build_spatial_launcher.py` 以此处批准的 1024 PNG 为唯一源。Android 入口直接使用同一 PNG；PICO 前层保留图案 RGB，增加圆角 alpha/SDF，后层为配套绿色底板。保留既有前后层顺序及两组 Manifest 元数据。
- 已覆盖五个旧 PNG，删除旧前景矢量、旧单色矢量、两个未使用的 adaptive icon XML 和旧底色配置，生成脚本不再包含旧图案。
- 离线 `:app:assembleDebug :app:lintDebug` 成功；Lint 0 错误、26 警告。APK 版本 1.0.21 / 21，应用和入口 Activity 均引用新图标；APK 内五个 PNG 与对应源资源逐像素一致，旧矢量不在包中。
- 未在本轮安装头显；系统启动器的缓存刷新与最终视觉显示待真机确认。构建与文件校验不等同于启动器视觉验收。
- GitHub 保存七张 PNG、提示词及规格说明；APK 和可重建 ZIP 仅留本地。
