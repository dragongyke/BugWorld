# BugWorld V2 实施与验证

2026-10-08。SDK 固定 **6.1.0**；工作分支 `codex/bugworld-v1`。已确认的设计是目标，下列真实产物与验证结果不等同于设计图或真机画质验收。

## 已实现

| 模块 | 当前行为 |
| --- | --- |
| 创作台 | 画紙、上方导航、右侧画具、左侧作品册分别为原生 WindowContainer；保留作品册选中项，进入 Stage 后收起，返回恢复原窗口集合 |
| 蜡笔 | 固定纸纹、方向性蜡痕、轻重与积色、按距离采样、历史触点与抬笔末点、镜像、撤销／重做；1024px 新画纸 |
| 模型 | 四类实际曲面模型；纸张 outline 与模型 surface 图案层分开；保留玩家笔触，甲片／翅膜／触角／腿及体节有独立 pivot；法线贴图使用切线与线性色彩空间 |
| 预览 | 画纸容器中的原生 SpatialView；旋转、缩放、蝴蝶展翅、关闭与失败重试；随所选作品版本加载模型 |
| 花园 | 蓝紫荷塘，真实荷叶／叶脉／树干／苔藓枝／荷花／芦苇／水面几何，远景全景纹理，暮色照明与萤火；138,768 三角，16 个静态材质批次 |
| 放生 | pending 请求先准备资源；Stage 可见且资源准备后提交；微光汇聚、昆虫渐显、短铃声与展示停留；满 10 只先渐退再补入；取消不会提前淘汰作品 |
| 作品 | v1 与 v2 模板、UV、图像和草稿分开保存；记住每类昆虫最近编辑的草稿版本；作品浏览／删除／重新放入花园 |
| 声音 | 原创 96 BPM 轻快钟琴／笛声循环，独立自然声与出场声；未复用现场录音，原曲名称及授权仍未确认 |

## 实际产物

- [四种实际模型渲染](../assets-src/v2/insects/insects-actual-models.png)、[实际画纸](../assets-src/v2/insects/insects-template-sheet.png)。这是 Blender 渲染，不是头显截图。
- [真实蜡笔算法样张](visual-redesign/2026-10-08/crayon-runtime-v2.png)、[实际画纸涂色](visual-redesign/2026-10-08/crayon-runtime-butterfly-v2.png)。来自应用的 Kotlin 算法，不是概念图。
- [实际荷塘模型渲染](../assets-src/v2/garden/garden-preview.png)、[可编辑荷塘](../assets-src/v2/garden/garden.blend)、[可编辑昆虫](../assets-src/v2/insects/insects.blend)。Blender 灯光与移动端显示仍有差异。
- [模型验证](../assets-src/v2/insects/insects-validation.json)、[昆虫 GLB 往返](../assets-src/v2/insects/insects-roundtrip-validation.json)、[环境 GLB 往返](../assets-src/v2/garden/garden-roundtrip.json)。

## 动画与绑定

[完整动画设计](Insect-Animation-Design.md) 共 33 种：蝴蝶 9、独角仙 9、瓢虫 8、毛虫 7。已接入程序动作层：三类飞虫各 8 种，毛虫 5 种，包含停留、移动、转向、触碰以及飞虫起飞／飞行／落地／手上停留。实际参与动作还取决于日常路径和手部输入。

Blender Python API 的骨架、权重、Action、GLB 导出与干净进程重新导入探针通过；现有 Blender 足够，无需另购软件。PICO 6.1.0 本地接口具有蒙皮与动画播放 API。正式模型目前使用分件变换，**尚未包含完整 Armature/Actions，也未完成整腿 IK 和连续软体蒙皮**。指尖只有位置锚，旋转／支持面仍需扩展；不能把程序腿摆动称为已实现脚底锁定。

## 验证记录

- Gradle：单元测试、Lint、Debug APK 构建通过。最新已跑 **59 项单元测试**；Lint 无错误，保留 SDK 模板／依赖版本提示。
- 四类模型：涂色顶点 UV 覆盖率 100%，每个涂色区域均对应模型，零退化三角。画纸／投影轮廓 IoU 95.91%–99.55%；该指标衡量模板与网格一致，不衡量与概念图的摄影质感一致。
- GLB：昆虫几何／UV／内嵌材质往返通过，渲染平均像素差 <0.2/255；环境网格数、三角数、UV、两张内嵌材质图通过。
- 独立代码评审：修复退出意图与放生提交竞态、旧版草稿被新版草稿遮蔽、旧模型命名与动画枢轴不兼容。
- 真机：PICO CLI 安装／启动成功；日志确认三个默认窗口 attached，作品册创建／关闭、Stage 可见后 ready → release committed → arrival effect 的顺序。设备日志使用自身日期，不作为实施墙钟时间。
- 截屏：头显唤醒后 PICO CLI 与 ADB 标准 screencap 仍返回 `Capturing failed`，未获得有效头显截图。预览的实际可见位置、视觉还原度、手部接触效果和 10 只帧率仍需真机观察／测量；不得标记为通过。

## 仍需打磨

Stage 已替换为真实资源，但距离概念图的复杂植被层次、湿润高光、柔和雾气与摄影级材质仍有差距。当前水纹以静态几何高光为主，没有实时水面反射。后续以真实头显画面作对照继续迭代，不能用设计图代替验收。

复现入口：`scripts/build_insects_v2.py`、`scripts/build_garden_v2.py`、`scripts/build_audio_v2.py`；校验入口：`verify_insects_v2.py`、`verify_garden_v2.py`、`verify_crayon.ps1`、`verify_animation.ps1` 及 Gradle 测试。
