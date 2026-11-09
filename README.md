# BugWorld

给昆虫涂色，把自己的画送进温馨的碧绿森林。原生 Android/Kotlin 应用，PICO Spatial SDK **6.1.0**。

## 当前版本

**1.0.14** 安装包位于 `deliverables/BugWorld-1.0.14.apk`。中文系统显示「我的昆虫世界」，英文系统显示 BugWorld。画具提供 20 色，主画板支持原地三轴转腕预览。Stage 返回时自动恢复画板，并按进入前的状态恢复作品册。[交付与验证](docs/visual-redesign/2026-11-04/Delivery-114.md)

- Shared Space：原生 TopBar、中央画纸、跟随画板的右侧画具、独立作品册及凝视反馈。
- 八种画纸可横向切换，依次为蝴蝶、独角仙、瓢虫、毛毛虫、蜻蜓、蜜蜂、工蚁、蚱蜢。每种支持蜡笔涂色、3D 预览与轻触回应。
- 作品册：保存、浏览、删除、继续编辑、放入花园；新启动默认空白画纸。
- Stage 支持十只居民。八种昆虫有 19 条出生与循环路线，同路错时出发。捏合可飞的昆虫再摊掌，可邀请它落在手上。[移动路线](docs/visual-redesign/2026-11-04/Routes.md)
- 单机，音乐为原创合成曲；没有命名、联网分享或播放列表功能。

## 构建与验证

需要 JDK 17+、Android SDK 35；本机路径写在不入库的 `local.properties`。

```powershell
.\gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
python scripts/verify_stage112_package.py
python scripts/verify_emerald_native_scene.py
python scripts/verify_paint_v3.py
python scripts/test_environment_hdr.py
```

包校验默认报告写 `.work`，不会覆盖留存 APK 或历史交付记录；显式 `--publish` 才更新留存包。覆盖安装保留作品：

```powershell
adb install -r deliverables/BugWorld-1.0.14.apk
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

缓存、旧诊断包、原始性能大文件及重复预览已清理，详情见 [清理记录](docs/maintenance/2026-10-27-cleanup.md)。历史目录名不代表它可删除：部分是当前资产生成链的输入。

[产品设计](BugWorld-Design.md) · [动画设计](docs/Insect-Animation-Design.md) · [用量](docs/Implementation-Metrics.md) · [复盘](docs/Troubleshooting-Retrospective.md)

使用 `codex/` 功能分支，禁止直接提交或推送 main。
