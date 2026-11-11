# BugWorld · 我的昆虫世界

给昆虫涂色，把自己的画送进温馨的碧绿森林。原生 Android/Kotlin 应用，PICO Spatial SDK **6.1.0**。

## 当前版本

**1.0.20**（2026-11-11）。中文系统显示「我的昆虫世界」，英文系统显示 BugWorld；TopBar 品牌保持 BugWorld。界面跟随系统支持中英文。

本地保留包为 `deliverables/BugWorld-1.0.20.apk`，APK 不提交到 Git。克隆仓库后可按下文构建，输出为 `app/build/outputs/apk/debug/app-debug.apk`。

- Shared Space：原生 TopBar、中央画纸、跟随画板的右侧画具、独立作品册及凝视反馈。
- 八种画纸可横向切换：蝴蝶、独角仙、瓢虫、毛毛虫、蜻蜓、蜜蜂、工蚁、蚱蜢。20 色蜡笔、填色、橡皮、撤销/重做及对称绘画；涂色映射到 3D 模型。预览位置固定在画板前，捏住后随手腕旋转，切换画纸时关闭预览。
- 作品册：保存、浏览、删除、继续编辑、放入花园；新启动默认空白画纸。
- Stage 支持十只居民。八种昆虫有 19 条出生与循环路线，同路错时出发。捏合可飞的昆虫再摊掌，可邀请它落在手上。[移动路线](docs/visual-redesign/2026-11-04/Routes.md)
- 单机，音乐为原创合成曲；没有命名、联网分享或播放列表功能。

## 最近更新与验证范围

| 版本 | 主要变化 | 记录 |
| --- | --- | --- |
| 1.0.20 | 去除毛毛虫 3D 背部被误映射的画纸黑边，保留玩家笔触 | [修复与渲染对照](docs/Caterpillar-120-Delivery.md) |
| 1.0.19 | 修复中央画板启动时消失；调整 Stage 返回恢复顺序，保留作品册状态与位置 | [画板交付记录](docs/Studio-119-Delivery.md) |
| 1.0.18 | 蚱蜢地面→树干→荷叶循环路线；掌面落点偏移调整 | [疑难复盘](docs/Troubleshooting-Retrospective.md) |
| 1.0.15–1.0.17 | 空间启动图标、画纸线条、蚱蜢贴图、预览旋转及蚂蚁路线修订 | [疑难复盘](docs/Troubleshooting-Retrospective.md) |

1.0.20 的 127 项单元测试通过，Lint 为 0 错误/35 警告，已覆盖安装到头显。毛毛虫黑带已通过实际 GLB 的 Blender 对照渲染检查，真机显示仍待确认。性能、手掌遮挡和视觉还原以各交付记录为准；不以加载成功或离线渲染代替真机验收，也不宣称所有场景稳定达到 90 FPS。

## 构建与验证

需要 JDK 17+、Android SDK 35，以及完整的 PICO Spatial SDK **6.1.0** Maven 仓库（含 UI **1.0.4** 传递依赖）。Android SDK 路径写入不入库的 `local.properties`；SDK 二进制不随源码发布。

```powershell
.\gradlew.bat '-PpicoSdkMavenDir=C:/path/to/pico-sdk-maven' :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

本机使用 `.work/migration-sdk` 作为上述 Maven 目录。普通构建直接使用已入库运行资产，无需重新运行 Blender。可选资产校验需要 Python、NumPy、Pillow：

```powershell
python scripts/verify_stage112_package.py
python scripts/verify_emerald_native_scene.py
python scripts/verify_paint_v3.py
python scripts/test_environment_hdr.py
```

APK 校验报告默认写 `.work`，显式 `--publish` 才更新留存包；绘画校验会刷新 `docs/V3-Paint-Verification.json`，提交前检查差异。覆盖安装保留作品：

```powershell
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.bugworld.app/.platform.LaunchActivity
```

包名 `com.bugworld.app`，最低 API 35，arm64-v8a。

## 目录

| 目录 | 用途 |
| --- | --- |
| `app/src` | 应用代码、测试与唯一运行资产目录 `main/assets/v3` |
| `assets-src/emerald-native-scene` | 当前可编辑原生森林，包含全部相对引用 |
| `assets-src/emerald-forest-v2` | 当前 Blender/GLB、HDR、来源、最终六视角与路线采样几何 |
| `assets-src/v3-review` | 已批准昆虫、线稿、图标、纹理和源模型 |
| `assets-src/expansion-114` | 蜻蜓、蜜蜂、工蚁、蚱蜢的可编辑母版、色区、制作脚本和回读验证 |
| `assets-src/stage111-geometry` | 当前昆虫派生模型；旧花园几何仍是森林生成链输入 |
| `scripts` | 当前生成、校验及通用诊断入口，见 [脚本索引](scripts/README.md) |
| `docs` | 设计、交付证据、性能结果、用量和失败复盘 |

重复预览和构建输出按 [维护记录](docs/maintenance/2026-11-11-cleanup.md) 清理；本地旧 APK 和部分临时缓存的删除受工具策略阻止，尚未完成。历史目录名不代表它可删除：部分仍是当前资产生成链的输入。当前模型母版、来源许可、失败复盘、性能和用量证据保留；临时输出放在 `.work/`，不要提交构建目录或 SDK 缓存。

[产品设计](BugWorld-Design.md) · [动画设计](docs/Insect-Animation-Design.md) · [用量](docs/Implementation-Metrics.md) · [复盘](docs/Troubleshooting-Retrospective.md)

使用 `codex/` 功能分支，禁止直接提交或推送 main。

## 许可证

原创代码、文档和资产采用 [MIT License](LICENSE)。第三方资产和 SDK 保持各自许可，详见 [第三方来源与许可](THIRD_PARTY_NOTICES.md)。
