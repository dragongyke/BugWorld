# BugWorld · v3 资产审核包

本目录保存 2026-10-09 已批准的四种昆虫真实资产与原始检查记录。当前 1.0.20 使用优化派生版，另四种昆虫母版在 `assets-src/expansion-114`，环境为碧绿森林。下文的“尚未接入”等描述是当时的审阅阶段记录，当前状态以 [项目首页](../../README.md) 为准。

打开 [review.html](review.html) 可按空间 UI、画纸、四种昆虫与荷塘场景查看批准设计和实际输出；也可以直接查看各目录的 PNG。网页不联网，不上传数据。

| 内容 | 首选预览 | 实际源资产 |
| --- | --- | --- |
| 空间 UI 资产 | `ui/boards/asset-layout-review.png` | 品牌、工具图标和排版 SVG；不包含 SDK 实现 |
| 线稿/昆虫图标 | `lineart/comparison-approved-vs-svg.png` | 四张 SVG 画纸、区域遮罩、独立小尺寸图标 |
| 蝴蝶 | `butterfly/03-natural-leaf-closeup.png` | `butterfly.blend` / `butterfly.glb` |
| 独角仙 | `beetle/natural_setting.png` | `beetle.blend` / `beetle.glb` |
| 瓢虫 | `ladybug/natural_setting.png` | `ladybug.blend` / `ladybug.glb` |
| 毛毛虫 | `caterpillar/03-natural-leaf-closeup.png` | `caterpillar.blend` / `caterpillar.glb` |
| 暮色荷塘 | `garden/garden-populated.png` | `garden-naturalized.blend` / `garden.glb`；图中昆虫来自各自独立 GLB |

各物种 `REVIEW.md` 记录造型、纹理、动画与导出检查。`asset-manifest.json` 指定这批交付候选的唯一文件和 SHA-256；中间 `.blend`、旧的迭代图片和运行日志不应当作运行时输入。

## 审核边界

- 自然环境图和中性光图均由真实 Blender 资产渲染，概念图仅并排作参考。
- 四种昆虫各有五个骨骼动画；动画片段为原地动作。场景路径、地形接触、手指停留与触碰触发留待应用阶段。
- 当前配色是静态审核样例。画纸到模型的 UV/区域约定已记录，玩家画作更新尚未接入。
- 此处为较详细的审核网格。移动端 LOD、材质合批、压缩与“10 只昆虫同场”性能尚未验收。
- 场景世界光、面积灯、体积雾与后期微光不能由 GLB 自动完整复现。后续需要单独实现并对照头显截图。
- 枯木、树根、苔藓的许可见 [来源记录](garden/ASSET-SOURCES.md)。其余自建昆虫和矢量资产使用本项目源脚本生成。

本轮只制作和审核资产。用户确认后才进入资产接入与应用逻辑实现。
