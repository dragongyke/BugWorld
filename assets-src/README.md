# 资产源文件

运行资源在 `app/src/main/assets/v3`；此目录保留可编辑主文件、生成依赖和必要证据，不会整体打进 APK。

| 目录 | 保留原因 |
| --- | --- |
| `emerald-native-scene` | 当前原生森林、日光、材质图和 73 个依赖文件；运行 bundle 从这里生成 |
| `emerald-forest-v2` | 当前 Blender/GLB、实拍 HDR、纹理、来源和最终六视角；路线采样依据 |
| `emerald-routes` | 当前路线采样结果与生成的 Kotlin 数据 |
| `v3-review` | 四种批准昆虫的 Blender/GLB、纹理、动画、矢量画纸与 UI；旧花园仍被生成工具引用 |
| `insects-batched` → `stage111-geometry` | 昆虫合批、几何简化链及来源清单 |
| `emerald-forest-review` | 第一阶段花园 GLB 与地面纹理，是第二阶段生成器的直接输入；重复预览已删 |
| `stage-ring` | 简化工具使用的旧花园几何/路线；不参与 1.0.12 运行加载 |
| `emerald-water-editor` / `emerald-native-materials` | 原生材质生成源；构建缓存及重复诊断图已删 |

`v3-review/asset-manifest.json` 和历次 manifest 是对应阶段的来源证据，**不能当作当前运行包的同步清单**。当前检查使用 `scripts/verify_stage112_package.py`；已删除会恢复旧环境的同步脚本。

当前森林打包：`python scripts/pack_emerald_runtime.py`。它移除审阅用固定昆虫后生成运行 bundle。HDR、路线与几何要同步更新，见 [脚本索引](../scripts/README.md)。

昆虫共 20 个动画片段。蝴蝶原始前方为 −Z，其余为 +X；应用包装层统一尺度与姿态。CC0 木材/苔藓来源见 [来源记录](v3-review/garden/ASSET-SOURCES.md)，新增森林素材来源保留在 `emerald-forest-v2/sources`。

清理前历史通过 Git 提交 `fb9545e` 查阅；未入库日志已压缩留存。概念图、Blender 渲染、原生编辑器和头显证据仍分别记录，不能互相替代。
