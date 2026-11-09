# 1.0.4 · Stage 光照与水面修正

## 问题与证据

用户提供的真机图只有蓝色轮廓高光，叶片与树干接近黑色，天空不可见，水面反光呈密集条纹。该图不同于 Blender 评审图，证明之前的构建、资产一致性及逻辑测试不能代表运行时画质验收。

设备日志确认 1.0.3 的 garden.glb 已加载，Stage 达到 ready，没有 GLB/KTX 加载异常。原实现同时创建两盏平行光，只有低亮度天空图转换的局部 IBL（指数 0），没有配置 Stage 全局环境光；水面也没有花园物体的环境倒影。

蓝色高光与第二盏冷色平行光一致，“第二盏覆盖主光”是待设备对照验证的假设，不把它当成已由日志证明的 SDK 限制。天空的 SDK 球体 UV、内侧剔除和可见性未经过实机验证，本次改为显式网格。

## 修改

- Stage 改为 `StageEnvironmentLightingComponent`，初始指数 8（256 倍原图辐射值）。保留一盏暖色平行光，2400 lux；冷色补光改为点光，1800 lm。指数是本轮校准起点，最终亮度以头显验收为准。
- 天空使用明确的向内三角形、全景 UV、内向法线和背面剔除，保留确认过的天空图片、32 m 半径、不受光材质与关闭色调映射。几何测试检查全部三角形方向、极点和接缝。
- 从确认的 `garden-naturalized.blend` 烘焙 1024×512 线性 HDR 反射探针，排除水面自身和预览体积雾，不修改模型主文件。保留超过 1 的辐射值，生成 5 级 GGX KTX，仅绑定 `pond_water`。
- 水面仍使用原模型和法线纹理，金属度改为 0、粗糙度 0.24、法线强度 0.16，减弱塑料感与密集尖锐高光。
- 新增 `BugWorldLighting` 日志，记录天空、IBL 与水面实际绑定。资源随 Stage 释放。

反射探针是静态近似，不包含昆虫的实时倒影和移动观察时的平面反射视差；本轮未实现动态水波。未宣称已还原 Blender 的实时反射、体积雾或后处理。

## 验证

- `testDebugUnitTest + lintDebug + assembleDebug --offline`：通过，87 项单元测试，0 失败；Lint 0 错误、31 项警告。
- `scripts/test_environment_hdr.py`：先观察到缺少 HDR 支持时失败，修改后通过；8 倍白色辐射值通过 KTX 写入/读取后保持，避免压成普通图片。
- 原天空 KTX、花园 HDR KTX 结构/数值检查通过；Blender 反射预览已人工检查，首个过于靠近莲花的探针已重新选位并重烘焙。
- APK 37 个运行资产；29 项确认资产核对通过，5 个原 GLB 保持字节一致，20 段动画，旧运行资产为 0。
- APK SHA-256：`6e8d57797d47495c2351ec9e59b9327f46588a505b0f8bda708617e598b13fd6`。
- 已通过 PICO CLI 替换安装并启动 1.0.4；保留作品数据。设备已连接且 Awake，但 CLI 截屏仍返回 `Capturing failed`。

**尚待验收：** 1.0.4 的实际天空显示、明暗层次、反射方向、手部观察距离及性能。安装成功与编译成功不等于视觉问题已解决。用户发来的旧版真机图作为问题证据，不作为修正后的截图。

## 复现与依据

1. 用 Blender 自动化 runner 打开 `assets-src/v3-review/garden/garden-naturalized.blend`，执行 `scripts/bake_garden_water_probe.py`，输出到同目录的 `lighting/`。
2. 执行 `python scripts/pack_garden_water_probe.py`；只验证时添加 `--check`。
3. 构建并替换安装 APK，进入花园，检查 `BugWorldLighting`、`BugWorldGarden` 日志和真实画面。

[PICO Stage 全局环境光](https://developer.picoxr.com/spatial-api/6.1.9/spatialpack/core/com.pico.spatial.core.ecs/-stage-environment-lighting-component/index.html)与[局部 IBL](https://developer.picoxr.com/spatial-api/6.1.9/spatialpack/core/com.pico.spatial.core.ecs/-image-based-light-component/index.html)文档说明了两者作用范围和指数含义。网页版本为 6.1.9；本项目以本机 6.1.0 SDK 实际编译通过为兼容性依据。指数 8 亦与本机 PICO SpatialVideo 示例 `RoomLighting.kt` 一致，但不同环境纹理仍需分别校准。
