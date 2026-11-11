# 瓢虫 · Blender 实体资产评审

本轮交付仅用于资产评审。模型、贴图和动作由本机 Blender 5.2.1 Python API 创建，可继续编辑；没有接入应用或设备。

## 造型与材质

- 两片有厚度、卷边和独立铰链的穹顶翅鞘；中间保留深色接缝。
- 左壳粉红，右壳薄荷青绿与黄色蜡痕；每片壳各有一个完整、沿身体纵向的深棕长椭圆斑点。
- 前胸为窄拱形护颈，连续深棕色纹样沿曲面展开。头、复眼、口器、触角以及六条分节腿独立建模。
- 使用独立 PNG Base Color、Roughness 和 Normal 图像。颜色 PNG 按 sRGB 字节写入，数据贴图按 Non-Color 读取；所有依赖打包进 Blend/GLB。
- `ladybug.blend` 是可编辑主文件；`ladybug-natural-setting.blend` 是叶片、叶脉与露珠布景的可编辑文件。

## 文件与检查视图

- `ladybug.glb`：模型、图像 PBR 材质、骨架与五个动画。
- `neutral_three_quarter.png`：真实中性灯光三分之四视角。
- `natural_setting.png`：真实叶片布景渲染。
- `roundtrip_neutral.png`、`roundtrip_flight.png`：新 Blender 进程重新导入最终 GLB 后的实际渲染。
- `animation_contact_sheet.png`：上排从左至右为 idle、walk、touch；下排为开壳、展翼、flight。重复单帧 `pose_*.png` 已清理，需要时可用生成脚本重新输出。

## 几何与动画

可涂区域约定见 `paint-region-binding.json`，关联 `assets-src/v3-review/lineart/manifest.json` 中 ladybug 的区域 1/2/3/4。左、右翅鞘分别拥有 `left_pink_wax` / `right_mint_wax` 材质；护颈使用 `ivory_collar_with_brown_smudge`。翅鞘 UV 的 U 从尾端到头端，V 从背部中缝到外侧边缘，V 是拱面角度域，不等同画纸像素的横向比例。后续需要把线稿区域裁切并映射到这些 UV；墨线与斑点保护遮罩也需接入。头部目前共享深棕 cuticle 材质，若要独立涂头还需材质实例化。当前 GLB 仅含固定评审纹理，动态用户画作映射尚未实现。

主模型有 139 个网格、36,108 个顶点、71,428 个三角形、34 根骨骼。每个网格均有 UV 与骨骼权重；GLB 包含 1 个 skin、10 个材质和 30 张嵌入图像。详见 `asset-validation.json`。

动作以 24 fps 导出：idle 72 帧、walk 36 帧、touch 42 帧、takeoff 60 帧、flight 48 帧。腿、翅鞘、触角、头与两段膜翅采用刚性关节权重。起飞先抬开翅鞘，再抬升折叠翼、展开膜翅，最后抬身并扇动；步行为原地动作。

`flight-clearance.json` 检查最终 GLB 的 takeoff 和 flight，共 214 个半帧样本，使用 0.03 mm 容差的三角形表面 BVH 相交测试。记录包含源 GLB SHA-256；核对的对象为四片膜翼网格与腹部、胸腹连接、前胸、双翅鞘。这个结果不代表任意动画混合、所有时间点或体积包含测试。脚底接触与地形 IK 不在此项检查中。

## 已知边界

最终文件核对结果：13 项必需交付文件均存在且非空；采样报告 SHA-256 与最终 `ladybug.glb` 一致，214 个样本未检出上述网格间表面相交。独立进程重新导入后保留 34 根骨骼和全部五个动作。已人工查看中性图、自然图、六姿态表和回导图；飞行视图已重新取景，翅鞘顶端完整保留。

这是较详细的资产评审网格，尚未制作设备用 LOD。步行没有连续脚底锁定或地形 IK；不同动作接入时仍应做短暂混合。膜翼为薄面与独立翼脉结构，关节不是连续软组织变形。自然布景为简化的实际几何。尚未进行 PICO 原生 SDK、Asset Bundle 或头显渲染验证。

继续编辑只需要现有 Blender，无需安装新软件。生成脚本为 `scripts/assets_v3_beetles.py`；渲染作业应串行运行。
