# 碧绿森林 · 可移交原生编辑器场景

此项目保存真实 PICO 原生材质与日光结果，避免仅依赖 `.work` 或编辑器缓存。**不是 Android 应用，也不是最终画质/帧率验收。**

## 打开和复现

1. 使用 Spatial Editor 6.1.0 打开 `emerald_native_scene.spatialproject`。
2. 环境 HDR 选择 `../emerald-forest-v2/sources/forest_slope_4k.exr`，intensity exponent **8**、rotation **0**。这是编辑器环境设置，场景文件未包含 Android Stage IBL 组件。
3. 眼点 `(0,1.6,0)`，坐姿 `(0,1.15,0)`；场景含唯一森林背景、一盏日光、完整花园及四只批准昆虫的固定姿态。
4. 从仓库根运行 `python scripts/pack_emerald_native_scene.py` 编译 mobile shader bundle；只为子进程补充同版本 SDK DLL 路径，不修改全局环境。
5. `python scripts/verify_emerald_native_scene.py` 核对源引用/哈希、组件与保留的水波截图，报告写 `.work`。可选 `--bundle assets-src/emerald-native-scene/Build/EmeraldForestReview.bundle` 核对重建包；不依赖旧 APK 或编辑器缓存。

## 本轮结果

- 73 个场景与依赖文件，127 个相对资源引用，无 `.work` 绝对引用。HDR 按上述单独设置。
- 原生项目重新打开后检查前/右/后/左、坐姿、抬头六视角；背景与日光投影同时存在。截图位于 `../emerald-forest-v2/editor-native-*-final.png`，网格/坐标轴为编辑器辅助显示。
- mobile 编译退出码 0；源文件尾部格式规范化后的最终重打包为 47.5 秒、207,779,138 字节；SHA256 `f3ab58b676826b4d5562336e902485c421bae623907c51734ea95026915686a3`。这是完整审阅包，含固定昆虫与编辑器资源，不能当作最终应用增量包大小。
- 新几何 150,789 三角形，背景 3,968；30 组主要表面相交检查为零。源几何统计不等于原生实际 draw calls，也不证明 72/90 FPS。
- 时间对照中水域变化、静态背景不变；透明水和阴影尚需真机开销对照。

`snapshot-report.json` 记录全部源文件哈希及 SDK 保存后旧路径修复，`pack-report.json` 记录移动编译，`verification.json` 记录自动验证。若编辑此项目后保存，需重新生成对应快照/编译报告，不能继续沿用旧哈希。

## 接入应用时必须配套处理

2026-10-22 已配套接入 1.0.12，见 [交付记录](../../docs/Stage-112-Delivery.md)。下列原则及真机待验项继续有效；1.0.11 APK 已不在本地留存，历史哈希和结果保留。

- 替换环境、背景、IBL 和原生水材质，同时重建新布局上的物种路线；不能只换 GLB 而继续使用旧路线坐标。
- 审阅用 `review_insects` 不作为运行昆虫，应继续从玩家作品创建原批准的带动画模型。
- 与保留的 1.0.11 对照加载时间、0/1/5/10 只虫的 GPU 与长帧、转头和手势体验。当前没有该证据，不能标为真机通过。
