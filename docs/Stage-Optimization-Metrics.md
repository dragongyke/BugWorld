# Stage 优化：测量、候选与验证

2026-10-19，原生 Android/Kotlin，PICO Spatial SDK 6.1.0。基线 `f0d5823`（1.0.4），功能分支 `codex/bugworld-v1`。

本轮已完成静态资产审计、优化候选、真实 GLB 渲染、路线验证与 Stage 性能埋点。原任务随后已将配套资产整体接入 **1.0.6**，完成 99 项单测、Lint 和 APK 校验，见 [集成结果](Stage-Integration-Results.md)。**头显未连接，尚未安装或测得设备 CPU/GPU 帧时间；转头抖动和黑边尚未验证解决。** 原始批准清单保持不变，新增派生资产清单记录优化后的身份。

## 可复核的基线与候选

候选：`.work/stage-optimization/candidate-v2/`；原文件：`assets-src/v3-review/garden/garden.glb`。最终配套清单为 `.work/stage-optimization/ready.json`，不要使用此前 `candidate/` 或 `green/` 中的第一轮水面实验。

| 项目 | 1.0.4 基线 | 最终候选 | 变化 |
| --- | ---: | ---: | ---: |
| GLB 字节 | 63,333,100 | 52,132,376 | −17.7% |
| 三角面 | 740,784 | 494,775 | −33.2% |
| 导出顶点（含法线/UV 拆分） | 685,975 | 557,647 | −18.7% |
| 网格 / glTF primitive | 150 / 150 | 49 / 49 | −67.3% |
| 材质 | 16 | 16 | 保留材质区分 |
| BLEND 三角面 | 104,934 | 0 | 苔藓改为 MASK，几何数量保留 |
| 水面三角面 | 57,800 | 2,048 | −96.5% |
| 贴图 RGBA8 基级估算 | 168.0 MiB | 108.0 MiB | −35.7% |
| 贴图 RGBA8 完整 mip 估算 | 224.0 MiB | 144.0 MiB | −35.7% |

**primitive 数只是提交成本代理，不是真实 Draw Call。** 原生批处理、视锥剔除、双眼、多 pass、阴影会改变实际提交数。RGBA8 估算也不是设备实测显存，未计驱动布局、加载临时缓冲、天空/IBL、用户画作及昆虫。

基线 GLB SHA-256：`37db7de882b9768a416be37054a4d176a3cf8dbec578141eb7eb8bede99c3b34`。候选：`97db51ae63cda21d1fd367a76aa0ed66a2565bbd5c399bc66ce64baf0337e2c5`。

证据：`.work/stage-optimization/baseline-audit.json`、`candidate-v2/audit.json`、`candidate-v2/build-report.json`。`scripts/audit_stage_glb.py` 可重新从实际二进制读取统计。

## 已发现的问题与修改

1. **树干确实悬空。** Blender 世界水面约 Z=−0.10 m，前景倒木最低点 Z=0.216812 m，右侧倒木 Z=0.067671 m。前景下移 0.34 m、右侧下移 0.19 m，最低点分别为 −0.123188、−0.123384 m。附着苔藓按原支撑面归属同步移动，竖直主树和根部位置保留。前景树干几何未减面，路线重新从实际候选采样，避免昆虫悬停在旧位置。
2. **提交分组较多。** 原有 48 片荷叶、54 个茎、33 个静态萤光点分别成对象；按材质及 4 m 空间区块合并，保留独立剔除区域、路线叶片名称与几何。
3. **透明苔藓成本显著。** 104,934 三角面、312,595 个基线导出顶点处于一个 BLEND 材质。候选采用 alpha MASK、阈值 0.35，保留透明贴图及全部草丛。它消除了混合排序需求，但不能消除 alpha 测试/遮挡开销；头显边缘闪烁与 MSAA 效果仍需检查。
4. **远处木材与花朵有减面空间。** 主竖木保留 45%，右倒木及两处根部保留约 40%，花瓣保留约 55%；近处倒木与路线荷叶保持原表面。近处木材颜色和法线保留 2K，仅 ARM 和较远根部贴图降为 1K。
5. **水面几何频率过密。** 原 28 m / 170 格网叠加约 0.3 m 周期、毫米级波高，产生较密几何法线变化。候选使用 32×32 格的宽缓小起伏及多方向细法线；粗糙度 0.17、金属度 0、法线强度 0.65。第一轮粗糙度 0.30 的水面过平，已弃用。按新位置重新烘焙静态 HDR 探针。**仍没有动态波纹、昆虫实时倒影或平面反射视差。**

## CPU、加载与 GPU 的证据边界

| 环节 | 本轮实测 / 检查 | 结论与后续 |
| --- | --- | --- |
| 文件读取 | 桌面 Python，热缓存 1 次预热+5 次采样，中位数 18.51 → 15.34 ms | 只用于桌面读取对照 |
| GLB JSON | 同一桌面测试，0.99 → 0.44 ms | 不包含几何处理，不等同 Android 原生 GLB 解析 |
| 嵌入图片解码 | Pillow 中位数 299.03 → 285.59 ms | 仅约 4.5% 改善；不能据资产体积下降宣称加载成倍加快 |
| 读取+JSON+图片总计 | 桌面中位数 318.58 → 301.54 ms | 不含原生实体、纹理上传和 GPU，不能外推到头显 |
| Android 加载 | 新增 `garden_native_load`、`garden_clone`、`garden_attach_materials`、`sky_ibl_load`、`water_ibl_load`、`sky_bitmap_decode`、`sky_texture_create`、居民/画作与 `prepare_total` 分段 | 需设备运行后采集；原生 load 边界不能把解析与 GPU 上传拆开 |
| 每帧逻辑 | `BugWorldStage:tick` trace；300 次回调窗口的墙钟/当前线程 CPU 均值、未钳位间隔 p50/p95/max | 不把逻辑 delta 上限 50 ms 当作真实帧间隔；隐藏/后台间隔排除 |
| Draw Call / GPU | 仅有 primitive/材质/透明面静态审计 | 实际 CPU 提交与 GPU 帧时间均待测 |
| 阴影 | 代码为一个投影阴影方向光、一个点补光；保留当前配置 | 需要同视角单独关阴影 A/B 才能归因；没有凭推测改掉照明 |
| 转头黑边 | 只有用户反馈，无本轮设备帧追踪 | 不将其直接判定为面数、剔除或合成器问题 |

桌面测试记录：`.work/stage-optimization/desktop-loader-proxy.json`。上述 CPU 时长不是净工时；操作系统进程 CPU 计数精度及调度会使其与墙钟略有差异。

新增日志标签 `BugWorldStagePerf`。加载挂起使用异步 Trace，普通 CPU 段使用同步 Trace。`first_visible_ready` 从 GardenRuntime 开始创建到资源就绪且可见三帧；它不包含点击按钮之前的时间。输出明确标注 app callback 不是 GPU/compositor FPS。没有修改 ModelLibrary 或昆虫动画接口。

## 本任务受影响文件

- `garden/GardenRuntime.kt`、`ui/GardenScene.kt`、`spatial/SceneLighting.kt`：加载/帧诊断；新增 `garden/StageDiagnostics.kt`、`garden/StageFrameStats.kt` 与 `StageFrameStatsTest.kt`。
- `scripts/assets_v3_routes.py`、`scripts/pack_garden_water_probe.py`：增加隔离候选的输入/输出参数，原默认工作流保留。
- 新增脚本：`audit_stage_glb.py`、`benchmark_stage_assets.py`、`build_stage_candidate.py`、`inspect_stage_blender.py`、`render_stage_comparison.py`、`verify_stage_candidate.py`、`verify_stage_bundle.py`、`verify_stage_kotlin.ps1`、`record_stage_metrics.py`。
- 本报告及 `Stage-Optimization-Usage.json`；可编辑模型、GLB、路线候选、渲染、KTX 与完整工具报告均在 `.work/stage-optimization/`。

以上是本 Stage 对话的文件范围。共享目录中 PreviewScene、ModelLibrary、BugWorldState、Main、build.gradle、绘画/UI、Shared Preview 文档和总统计的同期变化来自原任务，不归属于此补丁；本任务没有暂存、提交或推送任何文件。

## 实际渲染与静态验证

六张固定相机、同光照的真实 GLB 渲染位于 `.work/stage-optimization/comparison-v2/`：`baseline/candidate-overview.png`、`baseline/candidate-near-wood.png`、`baseline/candidate-water.png`（其中 `/` 表示两个前缀，实际文件名如 `candidate-water.png`）。可编辑场景为同目录 `baseline-review.blend`、`candidate-review.blend`；纯候选模型为 `candidate-v2/garden-stage-candidate.blend`。

检查结果：近景树皮、苔藓、叶脉保留；未见大片缺材质、透明黑片或主树轮廓破裂。水面不再显示原来的密集几何波纹，主树/花茎的反射可辨。降低前景倒木改变了画面下缘遮挡，这是修正悬空的预期影响。远处减面、alpha 边缘和水面质感仍需头显近看与转头检查。Cycles 的真实反射、面积灯和雾不等于 PICO 的静态探针与实时光照；这些图只证明资产对比。

- 几何门槛先在基线失败（面数、分组、水面网格与悬空），再在候选通过。门槛为 **少于 500,000 三角面**、不超过 85 个网格。
- `candidate-v2/verification/candidate-verification.json`：近树形状在所需位移后、两片路线荷叶的顶点距原表面最大偏差均为 0；三处木材与水面接触检查通过。
- `candidate-v2/route-verification/kotlin-surface-validation.json`：真实 Kotlin 采样 37,716 个地面姿态，最大表面距离 3.0367 mm（设计接触偏移 3 mm）；4,732 个巡航采样，最小实体净空 14.1241 cm。
- StageFrameStats 2 项测试、ApprovedGardenRoutes 7 项测试通过；StageRuntime/SceneLighting/Diagnostics 对 SDK 6.1.0 的直接 Kotlin 编译探针通过。**未运行 Gradle 全套测试、Compose 编译或 APK 构建。**
- HDR 探针 6 面、5 个 GGX mip、线性 R11F_G11F_B10F KTX 结构/数值通过；亮度最大值保留为 7.8125。报告 `candidate-v2/water-reflection-verification.json`。
- `verify_stage_bundle.py` 核对候选 GLB、材质 alpha、水面参数、路线、几何报告、6 张渲染及探针哈希，并确认原批准/运行 GLB 未改。
- 独立只读审查未发现 Critical/Important 问题。已补候选输出路径保护，防止误写批准目录或把新路线单独写回运行目录。审查中“499k”的描述为任务摘要笔误，最终门槛以上述 500,000 为准。

## 集成顺序与设备对照

本轮资产集合必须整体集成：`garden.glb`、`ApprovedGardenRoutes.kt`、`garden-routes.json`、`water-reflection.ktx`、水面参数。当前 `SceneLighting.applyToGarden` 仍保留基线 `.24/.16` 参数，集成候选时改为 `.17/.65`；不能只替换 GLB。原始批准 manifest 保持锁定，新增派生资产清单，且继续严格校验四种昆虫的原始身份。

协作文件：`.work/stage-interface-needs.md` 与 `.work/stage-optimization/ready.json`。在 `.work/shared-space-integration-complete.json` 出现且时间晚于本任务创建（2026-10-19 13:03:53，北京时间）前，本任务不做应用集成、Gradle、安装或头显操作。

设备验收按同一刷新率、同一作品集、同一视角进行：

1. 保存 1.0.4 与带诊断候选的包/设备版本、刷新率、温度与当前驻留作品数。各做冷启动和连续 3 次进出 Stage；每种记录加载分段及首次可见就绪时间。
2. 0 / 1 / 10 只昆虫分别静止观察、左右转头、近看树皮/水面；每段至少 30 秒，记录回调 p50/p95/max、逻辑 CPU 与墙钟、原生 CPU/GPU 帧时间（工具实际可用才记录）。在当前刷新率的帧预算下判断，不用回调 p95 直接宣称 GPU FPS。
3. 若逻辑 CPU 小而帧间隔大，仍需系统调度/原生渲染 trace 区分 GPU、JNI 提交或其他主线程阻塞。分别关闭阴影、隐藏水面、隐藏苔藓、隐藏花园、停止居民逻辑作单变量 A/B；使用诊断构建，不把这些消融状态交付为最终画面。
4. 检查两根倒木触水、苔藓跟随、出生/爬行接触、MASK 边缘、从不同角度看水面探针错位、转头黑边、10 只昆虫持续运行和反复退出释放。记录结果后再决定是否需要进一步 LOD、透明密度或光照调整。

## 本轮 PICO CLI 能力

| 实际调用 | 结果 | 统计口径 |
| --- | --- | --- |
| `pico-cli --version` | 0.5.0 internal，690164e | 已有版本查询能力 |
| `pico-cli --help`、`pico-cli perf --help` | 返回命令清单 | 仅帮助 |
| `pico-cli perf trace --help` | 失败：Perf utilities 0.2.0 未安装 | 未采集性能 trace |
| `pico-cli perf live --help` | 同上 | 未采集实时性能 |

本轮 CLI 共 5 次调用；业务能力仅复核版本查询，新增已验证性能能力为 0。不运行 setup/doctor 自动安装依赖；没有 ADB、设备操作或 Spatial Editor 操作。Blender、Pillow、Kotlin 编译、JUnit 及文件检查单列，不算 PICO CLI 能力。

## 时间与 Token

任务创建时间从本地会话元数据读取：**2026-10-19 13:03:53.579，北京时间**。墙钟含分析、脚本运行、渲染、审查与等待，不等同净工时。当前快照及每个会话明细见 [Stage-Optimization-Usage.json](Stage-Optimization-Usage.json)，由 `scripts/record_stage_metrics.py` 生成。

本轮仅计本 Stage 对话及一个直接只读审查代理。缓存输入包含在输入中，推理输出包含在输出中；不把账户百分比、工具未暴露用量或快照之后的请求计入。原 Shared Space 对话的同期增量不在这里重复统计。

与项目历史统计关联：[Implementation-Metrics.md](Implementation-Metrics.md)。最终集成时按会话 ID 将本快照贡献加到总统计一次，不能将之前的累计快照再次相加；没有足够数据在本阶段宣称一个覆盖父任务同期工作的项目总数。

<!-- STAGE-USAGE:START -->
本轮落盘快照：2026-10-19 13:25:34（北京时间），墙钟 **21 分 41 秒**；可核实合计 **6,206,215 Token**。

| 会话 | 输入（含缓存） | 其中缓存 | 输出（含推理） | 总 Token | 日志截止 UTC |
| --- | ---: | ---: | ---: | ---: | --- |
| stage_main | 5,377,091 | 5,221,504 | 39,540 | 5,416,631 | 2026-10-19T05:25:01.443Z |
| /root/stage_review | 784,119 | 718,848 | 5,465 | 789,584 | 2026-10-19T05:18:13.537Z |

以上不包含日志截止之后的请求或最终回复，独立审查时间不叠加到墙钟。
<!-- STAGE-USAGE:END -->

## 复现入口

本机 Blender runner：`C:/Users/Admin/.codex/skills/blender-automation/scripts/run_blender.py`；Blender 5.2.1；Pillow/NumPy 使用 Codex bundled Python。各 Blender 脚本均接受 `--output-dir`，runner 后续参数放在 `--` 后。完整执行命令记录在 `.work/stage-optimization/` 下各 `run-*.json` 中。

| 顺序 | 脚本与输入 / 输出 |
| --- | --- |
| 1 | `audit_stage_glb.py <glb> --output <json>`；基线与候选分别审计 |
| 2 | Blender `build_stage_candidate.py --output-dir <candidate>`；输出 GLB 和 packed blend，不改原资产 |
| 3 | Blender `verify_stage_candidate.py --output-dir <candidate>/verification --glb <candidate>/garden.glb` |
| 4 | 先复制原路线 Kotlin 到候选目录；Blender `assets_v3_routes.py --glb <candidate>/garden.glb --kotlin <candidate>/ApprovedGardenRoutes.kt --asset <candidate>/garden-routes.json --output-dir <candidate>/routes` |
| 5 | `verify_stage_kotlin.ps1 -RoutesPath <candidate>/ApprovedGardenRoutes.kt -CompileRuntime`；Kotlin CSV 输出到 `.work/stage-optimization/kotlin/candidate-poses.csv` |
| 6 | Blender `assets_v3_routes.py --glb <candidate>/garden.glb --verify-samples <csv> --output-dir <candidate>/route-verification` |
| 7 | Blender `render_stage_comparison.py --candidate <candidate>/garden.glb --output-dir <comparison>` |
| 8 | runner 以 `<comparison>/candidate-review.blend` 为输入执行 `bake_garden_water_probe.py --output-dir <candidate>/lighting` |
| 9 | `pack_garden_water_probe.py --source <candidate>/lighting/water-reflection-linear.npy --output <candidate>/water-reflection.ktx --report <candidate>/water-reflection-verification.json`；同参数加 `--check` 复核 |
| 10 | `verify_stage_bundle.py --candidate <candidate> --renders <comparison> --output .work/stage-optimization/ready.json` |

运行资产替换和最终 APK 校验需在协作门槛之后另行执行；以上入口不会安装或推送。
