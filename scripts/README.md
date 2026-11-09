# 当前脚本入口

从 BugWorld 根目录执行。历史版本同步/路线覆盖脚本、固定日期统计脚本及一次性诊断入口已清理；历史结果保留在 `docs`。

| 用途 | 入口 |
| --- | --- |
| 当前 APK/资产一致性 | `verify_stage112_package.py`；先运行 Gradle 单测/Lint/构建。默认报告写 `.work`，`--apk` 选包，`--publish` 才覆盖留存包 |
| 原生源引用/材质声明/保留的水波截图 | `verify_emerald_native_scene.py`；可选 `--bundle` 验证重建的审阅 bundle，未提供时不声称编译产物通过 |
| 运行/审阅 bundle | `pack_emerald_runtime.py` / `pack_emerald_native_scene.py`；需本机 PICO 6.1 编辑器打包器 |
| 森林源模型 | Blender 执行 `build_emerald_forest_v2.py --output-dir assets-src/emerald-forest-v2`；依赖 `build_emerald_forest_review.py`、`assets_v3_garden.py`、`build_stage_candidate.py` 和保留的上一阶段几何 |
| 森林素材下载 | `fetch_emerald_sources.py`，按来源清单获取 CC0 文件 |
| 森林 HDR | Blender 执行 `prepare_emerald_hdr.py --output-dir .work/emerald-hdr`，然后 Python `build_emerald_ibl.py`；数值检查 `test_environment_hdr.py` |
| 新路线 | Blender 执行 `build_emerald_routes.py --output-dir assets-src/emerald-routes`，然后 Python `integrate_emerald_routes.py`；运行 `verify_routes.ps1` 后可在生成器中加 `--flight-poses .work/v3-routes/kotlin-poses.csv` 检查飞行中心线 |
| 昆虫派生链 | `merge_insect_draws.py` → `simplify_stage_models.mjs` → `verify_stage111_geometry.py`；Node 依赖可重装：`npm install --prefix .work/meshopt --ignore-scripts meshoptimizer@1.1.1` |
| 绘画映射 | `verify_paint_v3.py`；画纸/UI/音频生成分别为 `assets_v3_lineart.py`、`assets_v3_ui.py`、`assets_v3_audio.py` |
| 单项 Kotlin 检查 | `verify_core.ps1`、`verify_animation.ps1`、`verify_crayon.ps1`、`verify_routes.ps1`；完整回归以 Gradle 为准 |
| 真机语义检查 | `verify_studio_device.py`、`verify_studio_cold_start.py`、`stage_device_action.py`；不能代替视觉或手势验收 |
| 性能和用量 | `perf/*.sql`；`record_diagnostics_metrics.py` 的 `build_snapshot` 传入真实阶段起点，避免重复计算历史用量 |

其余 `assets_v3_*` 和审阅脚本是模型的生成/对照依赖。只提交正式主文件、必要证据与来源，生成的缓存、自动备份与逐帧图片不长期保留。

普通应用构建不需要重新生成所有资产；当前运行资源已入库。修改模型、路线或原生场景时，再重建对应产物并验证。
