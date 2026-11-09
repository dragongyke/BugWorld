# 原生水材质工作台

> 2026-10-27 清理注记：本文保留该阶段的成功/失败记录；重复预览、缓存和过期入口已删除，当前入口见 [资产索引](../README.md)。被清理的已跟踪文件可从 Git `fb9545e` 查看；不要把历史阶段状态当作当前验收。

PICO 6.1 工具链，独立于应用。**编辑器小样与移动端编译验证，不是头显画质或性能验收。**

## 当前实现

- 一个平面、共享 1024 法线贴图，两个尺度和方向不同的 UV 流动层。
- ShaderGraph 的时间节点驱动，不需要应用每帧上传纹理或重建网格。
- 金属度 0、IOR 1.333；同源森林 HDR 提供环境反射。
- 正确切线空间下的证据为 `water-final-t0.png`、`water-final-t1.png`；固定相机与水面内部区域的变化见 `animation-evidence.json`。早期 `water-basis/dual/calm` 图是诊断，不是最终材质效果。
- `Sources/Materials/EmeraldWater.usda` 为可读源；`EmeraldWaterValidated.usda` 为编辑器规范化结果；`Sources/Scenes/Hi.usda` 保存探针平面。

## 关键诊断

1. `ND_image_color3` 的 color3 输出不能直接接 float3 法线；编辑器结构校验曾报兼容，但运行日志仍报类型不匹配。改为 `ND_image_vector3`，并用发光纹理单独确认图片和 UV 可用。
2. 普通法线节点默认将切线法线转换到世界空间；本地 `mx_UsdPreviewSurface_surfaceshader.glsl` 将输入直接写入 `MaterialInputs.normal`。在这里混入世界 Y 向上的基向量会产生很强的碎亮点，不能以“可见波纹”作为正确性的证明。最终解码使用切线基 `(0,0,1)`、`(1,0,0)`。
3. 正确法线在默认工作台灯光下非常不明显；改用匹配的森林环境光，从低观察角度检查反射，并保留固定相机的时间对照。透明度、真实水底和完整花园尚未接入。
4. 两次 MCP 打包均返回 10008。直接启动进程得到 Windows `0xC0000135`，导入表确认缺少 `nanobind.dll`；同版本 SpatialEditor 带有该文件。`scripts/pack_emerald_water.py` 仅在子进程 PATH 中加入该目录，打包通过；没有复制 DLL 或修改全局 SDK。

## 复现及限制

打开 `emerald_water_editor.spatialproject`。`python scripts/pack_emerald_water.py` 生成 `Build/EmeraldWater.bundle`，结果见 `pack-report.json`。编辑器缓存和构建目录不入库。

最终水样仍为不透明 PBR；实际透明水底、整场景色泽、入水边缘、纹理驻留与增量 GPU 开销，需要集成后真机验证。之前提出的 ≤0.5 ms 只是预算，不是已测结果。
