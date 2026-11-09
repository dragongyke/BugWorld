# 荷塘资产来源

本文件记录实际模型与材质来源。设计图只用于构图对照，没有作为场景背景或贴图冒充三维资产。

| 来源 | 作者 | 本轮用途 |
| --- | --- | --- |
| [Dead Tree Trunk](https://polyhaven.com/a/dead_tree_trunk) | Rob Tuytel | 直立断木主体；调整方向、粗细、根部收分和破口；2K PBR 贴图 |
| [Dead Tree Trunk 02](https://polyhaven.com/a/dead_tree_trunk_02) | Jenelle van Heerden / Rico Cilliers | 扫描枯木，调整方向及比例作为前景、右侧倒木；2K PBR 贴图 |
| [Tree Stump 01](https://polyhaven.com/a/tree_stump_01) | Rob Tuytel | 根部与矮树桩；2K PBR 贴图 |
| [Moss 01](https://polyhaven.com/a/moss_01) | Rob Tuytel | 苔藓簇几何及 1K 透明叶片纹理；沿枯木表面散布并按材质合并 |

以上下载资产采用 [Poly Haven CC0](https://polyhaven.com/license)。许可针对下载资产，不包括该站示例图片、文字和商标；本轮没有使用这些示例图片制作贴图。

`sources/<资产>/SOURCE.json` 保留文件 URL、大小、SHA-256；下载脚本核对了官方 API 的 MD5。`publisher-files.json` 保留本次元数据。没有下载或运行第三方执行程序。

曾试用的 `dead_quiver_trunk` 由于颜色、轮廓不适合本场景而被淘汰；只保留来源缓存，不进入最终场景或交付清单。

源苔藓 glTF 虽声明透明混合，其颜色图引用的是 JPG；本轮另取官方 `moss_01_alpha_1k.png`，核对 MD5 后连接透明输入。最终 GLB 必须包含有 0–255 Alpha 的合成图像，避免把黑底渲染为实心叶片；打包脚本检查这一点。

荷叶、叶脉、茎、露珠、芦苇、荷花、水面和萤火点为本项目脚本生成的可编辑几何。荷叶基础颜色及审核世界背景沿用项目已生成的原创环境纹理；本轮调整叶片颜色并烘焙法线，生成独立粗糙度、水面法线和花瓣图像纹理。旧版昆虫模型没有进入本轮场景。

这些原创环境输入已独立归档在 `sources/project-original-textures/`；生成脚本不再读取 `app/` 中的旧资产路径。它们是先前本项目生成的叶片、树皮及天空纹理，不是商场视频、批准概念图或第三方网站截图。

生成入口：`scripts/assets_v3_garden.py` → `scripts/assets_v3_garden_naturalize.py` → `scripts/assets_v3_garden_roundtrip.py`。最终可编辑场景为 `garden-naturalized.blend`，便携几何/材质为 `garden.glb`。

Blender 中的环境光、面积灯、体积雾、反射和后期微光是审核场景设置。GLB 不包含这些效果的完整实时实现；后续需要在 PICO 引擎单独制作和核验。
