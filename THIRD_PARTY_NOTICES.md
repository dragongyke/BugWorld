# 第三方来源与许可

根目录 [MIT License](LICENSE) 适用于本项目原创代码、文档和资产。下列第三方内容保持其原有许可，不因项目采用 MIT 而重新授权。

## 森林模型、纹理与环境光

Poly Haven 下载资产采用 [CC0](https://polyhaven.com/license)。来源、作者和下载文件哈希保留在以下记录中；这些许可不涵盖网站文字、商标或示例截图。

| 内容 | 本地来源记录 |
| --- | --- |
| 枯木、树桩、苔藓 | [荷塘来源说明](assets-src/v3-review/garden/ASSET-SOURCES.md) 及该目录 `sources/*/SOURCE.json` |
| 蕨类 | [fern_02](assets-src/emerald-forest-v2/sources/fern_02/SOURCE.json) |
| 苔藓岩石 | [rock_moss_set_01](assets-src/emerald-forest-v2/sources/rock_moss_set_01/SOURCE.json)、[mossy_rock](assets-src/emerald-forest-v2/sources/SOURCE.json) |
| 地表落叶 | [forest_leaves_02](assets-src/emerald-forest-v2/sources/forest_leaves_02/SOURCE.json) |
| 森林全景与 HDR | [forest_slope](assets-src/emerald-forest-v2/sources/forest_slope_SOURCE.json)、[全景处理记录](assets-src/emerald-forest-v2/panorama-source.json) |

导出到 GLB、原生场景或应用资源中的派生内容沿用相应来源许可。批准概念图和项目生成的审阅图不是 Poly Haven 示例截图。

## SDK 与工具依赖

- PICO Spatial SDK 及编辑器遵守发布方随附协议；本仓库的 MIT 不授予其使用或再分发权。SDK 缓存不提交到 Git。
- AndroidX、Kotlin、Gradle 等依赖按各自发布物中的许可证使用；版本见 [依赖清单](gradle/libs.versions.toml) 和 [构建配置](app/build.gradle.kts)。
- Blender、Python、Pillow、NumPy 和 meshoptimizer 是可选资产制作/校验工具，遵守各自许可。本仓库不打包这些工具的安装目录。

本文件是来源索引，不替代依赖原有的版权声明、许可证和通知。
