# 森林场景 · 原生材质对照

这是 6.1 Spatial Editor 的材质兼容性证据，不是新 APK 或头显验收。

## 2026-10-21 最新状态

下面旧记录保留诊断过程；**当前完整源项目与编译结果以 [emerald-native-scene](../emerald-native-scene/README.md) 为准**。

- 场景使用 `WaterShallow.usda`：透明度 0.65、双层时间 UV、水下染色池底。`Water.usda` 保留为不透明对照；没有物理折射。
- 当前七种显式材质为水、池底、叶片、石头、花瓣、岸、蕨类，见 `bindings.json`。`Fern.usda` 独立读取 alpha，保留 MASK 裁切并修正偏白。
- `NativeSun.usda` 使用真实 `DirectionalLightComponent`，2400 lux；`ForestBackground.usda` 引用层保存不投射阴影策略，重开后仍生效。旧 `ForestSun.glb` / `ForestSun.usda` 仍是失败样本，不使用。
- 原生视口 `editor-native-*-final.png` 包含六个视角；固定相机水面两帧的水域平均 RGB 差 4.545、静态背景差 0。只证明动效，不证明 GPU 开销。
- 当前完整 mobile bundle 编译成功，最终格式规范化重打包为 207,779,138 字节；这是审阅包，不是最终应用增量包。旧 `pack-report.json` 和 `pack-shore-v3-report.json` 为历史/中间样本。
- 此目录绝对纹理路径可由脚本重建；便携项目全部使用相对资源引用。原生编辑器证据已经覆盖日光阴影，Android 头显画质、路线与性能尚未验证。

## 10 月 20 日诊断过程

- `Water.usda`：将独立工作台的双层流动法线接到真实花园的 `pond_water`；160 三角形池面，无网格逐帧更新。12 m UV 范围使用 3 倍平铺，法线强度从探针的 2 降至 0.4，粗糙度 0.10，避免背向亮天空时像白色湍流。使用匹配的森林 IBL。当前为不透明水面，不具备浅水折射。
- `Rock.usda`：显式绑定扫描石的颜色与切线法线，修复编辑器导入后白石头的问题。
- `Petal.usda`：显式绑定烘焙花瓣渐变。石头和花瓣使用 Power 2.2 近似纹理线性化；不宣称精确色彩校准。
- `bindings.json`：三种材质在真实花园中的目标。每次应用前须验证 USDA，预览实际像素后再保存。
- `ForestSun.glb`：**失败诊断样本，不使用**。导入后仅得到 Xform；灯光查询失败，不能声称已有日光或投影。应用现有日光需在集成时单独验证。

`scripts/prepare_emerald_native_materials.py` 从已登记来源复制纹理并生成 USDA。文件中的绝对纹理路径由该脚本生成，迁移机器后须重跑。本轮工作场景在 `.work/emerald-native-final`；它是可重建缓存，不作为正式源资产。

原生视口证据在 `../emerald-forest-v2/editor-*.png`。`editor-front-baseline.png` 是首次导入的白石头/材质差异；`editor-front-materials.png` 是较高岸线的中间样本；`editor-*-integrated.png` 才是低岸线与原生材质合在一起的样本。蓝色轮廓、网格或坐标轴属于编辑器辅助显示。

尚未验证：头显性能、原生日光阴影、昆虫路线和完整动画。四向截图不等于 100% 还原或流畅度达标。

完整编辑器场景的移动端材质包已编译成功：`pack-report.json` 记录退出码 0、约 121 MB 的诊断 bundle。它包含编辑器导入资源，不作为应用安装包或优化后的交付体积；不能据此判定 GPU 开销。编译输出保存在 `.work`，没有安装到头显。
