# 1.0.9 环绕荷塘资产

> 2026-10-27 清理注记：本文保留该阶段的成功/失败记录；重复预览、缓存和过期入口已删除，当前入口见 [资产索引](../README.md)。被清理的已跟踪文件可从 Git `fb9545e` 查看；不要把历史阶段状态当作当前验收。

真实 Blender/GLB 资产；`front/right/back/left.png` 是导出 GLB 重新导入后的 Cycles 渲染，**不是 PICO 真机截图**。

## 内容与来源

- 保留已批准单体尺寸；10 片荷叶、4 朵花、6 组稀疏水草、2 个木质主体，围绕 Stage 原点排列。倒木及树干沿用批准的 CC0 资产，授权记录见此前 `v3-review` 资产资料。
- `garden-ring.blend`：打包纹理的可编辑源文件，含审阅灯光、星空与前向相机。`garden.glb`：运行资产的同一份副本。
- `sky-source.png`：内置 imagegen 生成的 2:1 星空纹理，完整提示词见 `imagegen-prompt.json`。从 LDR 图计算环境光，不宣称是实拍 HDR 天空。
- `lighting/`：从此场景烘焙的线性 HDR 静态水面反射、预览、KTX 和数值检查。没有动态昆虫倒影或平面反射视差。
- `garden-routes.json` 与 `ApprovedGardenRoutes.kt`：在实际重导入 GLB 表面采样的 13 条路线；模型哈希写入路线文件。

## 复现

使用 Blender 5.2 后台运行 `scripts/build_ring_garden.py --output-dir assets-src/stage-ring`。推荐通过本机 blender-automation 的 `run_blender.py` 启动。脚本从 Git 提交 `6c81604` 提取批准的 1.0.8 GLB，避免循环使用新输出作为输入。

将输出 GLB、路线 JSON、Kotlin 路线文件同步到对应运行目录；将天空复制到 `app/src/main/assets/v3/environment/sky.png`，用 `scripts/assets_v3_environment.py` 重建 `sky.ktx`。

打开新 `.blend` 后执行 `scripts/bake_garden_water_probe.py --stage-offset 0 0 0`；用 `scripts/pack_garden_water_probe.py` 转换线性 NPY 为运行 KTX。

先运行 `scripts/verify_routes.ps1` 生成真实 Kotlin 轨迹，再用 Blender 运行 `scripts/verify_ring_garden.py`。报告检查主要实体相交、木头入水及路线贴面；不代替动画足部/翅膀碰撞、真机材质和性能验收。

明确接入运行文件后执行 `scripts/record_ring_manifest.py` 记录协调派生清单，再用 `scripts/assets_v3_runtime.py --stage-derivative assets-src/stage-ring/manifest.json --apk deliverables/BugWorld-1.0.9.apk` 检查 APK。此步骤不更改原始批准批次的身份清单。

## 已核实

251,260 三角面、36 个网格；相对 1.0.8 的 494,775 面减少 49.2%。运行 GLB 从 52,132,376 字节降到 32,875,460 字节。

主要荷叶与木头之间无相交；37,716 个实际 Kotlin 地面轨迹样本距对应表面最大 3.044 mm。详见 `build-report.json`、`geometry-verification.json`。
