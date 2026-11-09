# BugWorld 昆虫动画与绑定设计

2026-10-08。用于已批准模型的实施交接；本文件及 `assets-src/v2/animation-probe` 是设计和可行性证据，不表示四种正式模型已绑定或真机动画已验收。依据 [模型评审](visual-redesign/2026-10-08/Model-Review.md)、06–09 模型设计图及 [产品设计](../BugWorld-Design.md)。新增要求包含蝴蝶、瓢虫和独角仙飞行与叶片／花朵／手指停留。

## 1. 实施选择与已验证边界

**无需安装新软件。现有 Blender 5.2.1 LTS + Python API 可以做骨架、权重、动作和 GLB 导出。** 原生 Kotlin PICO SDK 也有蒙皮与动画播放接口；本项目现有 JSON 加载器尚未接入这些能力。

| 层次 | 已验证 | 不能据此声称 |
| --- | --- | --- |
| Blender 制作 | 探针建立 3 根连通骨骼、连续网格、每点最多 2 个权重、idle/crawl/recoil 3 个 Action；导出 GLB 有 skins、JOINTS_0、WEIGHTS_0、3 段 animation | 四种正式昆虫已经具备完整绑定 |
| Blender 往返 | 新进程导入后保留骨骼、权重、动作，播放不同帧确有网格变形；源场景静止／弯曲图已查看 | PICO 中的导入、材质、动画混合与性能已通过 |
| 本地 PICO API | `Entity.load/loadSuspend`、`ModelFormat.GLTF`、`findSkinnedMeshEntity`、`getAnimationResources`、`playAnimation`；`MeshResource.hasSkeleton/getSkeleton`；PlaybackController 的 time/speed/pause/resume/stop | 本地 SDK 的任意 glTF 扩展、IK、动态骨骼改姿均受支持 |
| 当前 BugWorld | JSON → `MeshModel` → 分件 Entity → `TransformComponent`，已有部件摆动 | JSON 已包含骨骼、inverse bind matrices、weights 或 Action；`SkeletonJoint` 是可直接设姿的骨骼 |

本地检查依据 `.work/sdk/core.jar`，对应项目 BOM `6.1.0`，SHA-256 为 `E69A8FE27A208C3276292EFD95C3F1E6B5CA633AA80D133018C10CF48945A875`。完整类签名保存在 [SDK 接口记录](../assets-src/v2/animation-probe/sdk-api.txt)。`MeshModel` 构造参数只有位置／索引／法线／切线／UV／颜色，未提供蒙皮数据入口。`SkeletonJoint` 公开字段只有名称、索引、父索引，不能据此假定存在运行时骨骼 IK setter。本地没有公开的 `SkinnedMeshComponent` 类，避免照搬其他引擎同名组件。

官方原生文档确认 [GLB/glTF 加载路径](https://developer.picoxr.com/spatial-api/6.0.0/spatialpack/core/com.pico.spatial.core.ecs/-entity/-companion/load.html)、[Entity 的蒙皮查找与播放](https://developer-cn.picoxr.com/spatial-api/0.12.2/spatialpack/core/com.pico.spatial.core.ecs/-entity/index.html) 和 [动画过渡配置](https://developer.picoxr.com/spatial-api/6.0.0/spatialpack/core/com.pico.spatial.core.ecs.animation/-animation-play-config/index.html)。在线版本与项目版本不同，具体可用签名以本地 jar 为准；本方案不依赖 Unity Animator、Unity Animation Rigging 或 Unity 插件。

**第一实现：** 采用现有分件模型 + 程序姿态 + 表面约束，蝴蝶／甲虫以翅根和腿根旋转实现；毛虫使用受限节链。行为、路径与部件姿态分开更新。骨骼 GLB 为下一可验证的加载后端：先在真机加载本探针、枚举资源并播放，再切换正式连续软体网格。不要为了动画先切换引擎。

## 2. 资产与 rig 接口

### 坐标、原点和命名

沿用模型 Agent 当前命名，不依赖 Blender 自动附加的 `.001` 后缀。运行时 JSON 为米制、Y-up；蝴蝶／瓢虫朝 `-Z`，独角仙／毛虫朝 `+X`。导出转换由模型脚本负责一次完成，运行时不能重复套 Blender→SDK 轴转换。翼角以下以“与背部展开平面夹角”描述，实际左右符号及旋转轴来自 rig 配置。

所有网格顶点是相对各自 pivot 的局部坐标，初始 `Transform = translation(pivot)`。如果增加父子层级，子节点平移改为 `childPivot - parentPivot`；不能把现有绝对 pivot 原样放进局部坐标，否则发生双重偏移。

| 昆虫 | 现有／本轮约定名称 | 逻辑绑定和转轴 |
| --- | --- | --- |
| 蝴蝶 | `thorax, head, abdomen`；`wing_left_upper/lower, wing_right_upper/lower`；`leg_-1_0..2, leg_1_0..2`；`antenna_-1/1` | body_root→thorax→head／abdomen／4 翅／6 腿；触角随 head。现有翅根约 `(±.006,.067,-.004)`，沿身体纵向局部 Z 旋转；前后翅可差相 10–18°，不拆出缝隙 |
| 独角仙 | `abdomen, pronotum, neck, head/horn`（按导出清单解析）；`elytron_left/right`；`flight_wing_left-1/right1`；同格式腿／触角 | body_root→胸部→头角／左右甲片／左右膜翅／腿。horn 随头整体转，不能独自弯曲；甲片和后翅根分离，主纵向为 X。模型 Agent 已确认补后翅及左右甲根 Z 偏移 |
| 瓢虫 | `head, pronotum, abdomen`；`elytron_left/right`；`flight_wing_left-1/right1`；同格式腿／触角 | 头及触角随胸部，左右甲片独立开合，飞行膜翅不共享甲片枢轴；主纵向为 Z |
| 毛毛虫 | `segment_0..7, head, tail, flexible_cuticle`；`proleg_{0..7}_{-1/1}` | `body_root→segment_0→…→segment_7→head` 为尾到头的逻辑链，tail 跟 segment_0，腹足跟所属节。位置由等弧长中心线求解；不能逐节独立上下浮动 |

实际部件应从最终 JSON 清单绑定；缺少必须部件时记录清晰错误并降级为静止，不能用模糊 `contains("left")` 判断所有资产。飞行膜翅沿用 `flight_wing` 前缀以兼容现有隐藏规则。独角仙头若与角合网，建立虚拟头控件同时驱动相关 part，无需强改资产名。

建议新增独立 rig 元数据，而不改变绘画 UV：`forwardAxis`、`parts[name].parent/pivot/hingeAxis/restRotation`、`limits`、`anchors`、`legRestLengths`。镜像通过左右关节旋转符号处理，不对根节点用负缩放。

### 骨骼与权重的制作规则

- **硬体：** 胸／头／甲／角每片刚性绑定 1 根骨骼（或直接 Entity）；翅主部 100% 随根骨，翅端若需要柔性加 1 根 tip 骨，局部权重渐变。不要让甲缝被左右骨骼拉软。
- **六足：** 正式近观 rig 每腿 coxa→femur→tibia→tarsus，控制器用 femur/tibia 两段 IK + 足尖端点；模型当前各腿为一整件，第一版只支持腿根摆动。整腿刚体无法同时保持髋端、足尖和弯膝位置，不能将这种降级写成“已实现 IK／无脚滑”。近手或慢速近观验收前应拆分两段腿网格。
- **毛虫：** 8 个体节骨 + 头、尾；连续皮肤每点最多 4 权重（一般 2 相邻节足够），归一化为 1。节中颜色主区高权重，关节褶皱处平滑混合；UV 按静止形体保存，不能逐帧重投影。腹足根随对应节，足尖接触控制独立。
- **导出：** 原地动作，body_root 不带世界路径位移；使用命名 Action，烘焙控制约束到骨骼 TRS，以采样曲线导出。GLB 中保留 skin/weights/animations。每个昆虫独立骨架，避免跨模型引用和重复骨名。
- **软体首版边界：** 分节模型可用相邻节重叠、受限弯角（每节约 2–4°）和 ≤8% 纵向压缩做轻缩。`flexible_cuticle` 若仍是刚性整块，不能跟随大弯曲；抬头／转叶背大幅动作必须限制，或切成随相邻节连接的短过渡片。完整连续皮肤需要蒙皮后端；不推荐以每帧重建网格掩盖这点。

## 3. 动作清单

以下为温和、易辨认的艺术节奏初值，不是生物学测量。每个动作都以当前姿态进入，用 0.12–0.25s 姿态过渡；时长中的范围按实例固定种子抽样，避免每帧随机。飞行的幅度／频率用连续相位，切状态不重置相位。

### 蝴蝶（9 种）

| 动作 / 触发 | 时长与循环 | 姿态要点 | 退出与衔接 |
| --- | --- | --- | --- |
| `idle_perch` 到达栖息点 | 2.8–4.5s 循环，停留 4–10s | 足尖固定；翅轻开合 12–28°，腹部微动；触角不对称探索 | 行走先卸载一组足；起飞先进入蓄势 |
| `walk` 同一叶／花上小范围调整 | 步周期 0.65–0.9s，按位移循环 | 小步交替三足；胸部朝路径切线；翅保持较合拢，避免扫叶 | 支撑足落稳后停，速度减至零后转 idle |
| `turn` 目标方向差 >20° | 0.45–0.85s 单次或分段 | 外侧迈步稍长，头先转、胸跟随，航向连续 | 与 walk 混合；不原地瞬间翻 180° |
| `touch_fold` 轻触身体附近 | 0.85–1.25s 单次 | 0.15s 收翅至 65–78°，稍抬触角；保持足点，停 0.2s 后松开 | 触碰冷却 2s；回原停留状态，飞行中改用轻偏航回应 |
| `takeoff` 邀请／换花／离手 | 0.55–0.8s 单次 | 屈腿蓄势→两次增幅拍翅→离面；离地后收足，抬升至少半个身体高度 | `lift_off` 事件释放足点，进入 flight |
| `flight` 航路移动 | 0.18–0.25s 翅循环；路径 1.5–4s | 可视扇翅 4–5.5Hz，10–75°；下拍较快，上拍较慢；小幅胸部俯仰 | 临近落点先降速，进 approach；不在贴手时持续大幅扇翅 |
| `bank_turn` 飞行切线弯曲 | 0.4–0.9s 可叠加 | 根节点侧倾 6–14°、头沿弧线；左右拍翅幅度差 ≤10% | 曲率减小时侧倾归零，不把整只昆虫倒向手部 |
| `land` 叶／花／手指落点稳定 | 0.65–0.95s 单次 | 预伸足→沿法线减速→前／中足接触→重心落稳；末段减小翅幅 | `touch_down` 绑定表面锚；全部足稳定后进入 idle 或 hand_perch |
| `hand_perch` 指尖／掌心落稳 | 3–6s 循环停留 | 翅小幅开合，足随手局部坐标；头部朝玩家轻探 | 正常经 takeoff 离手；手追踪失效走安全离开流程 |

### 瓢虫（8 种）

| 动作 / 触发 | 时长与循环 | 姿态要点 | 退出与衔接 |
| --- | --- | --- | --- |
| `idle` 叶面停留 | 2–3.6s 循环，停 3–8s | 合甲，触角交错小摆，足尖保持接触，身体无持续弹跳 | 先启动一组腿再平移 |
| `walk` 叶脉路线／爬上可接近手指 | 步周期 0.45–0.7s | 三足交替，相位 A=L前+R中+L后，B 相反；身体起伏 ≤体高 3% | 减速时同步降步频与步长；落脚后停 |
| `turn` 叶缘或路线变向 | 0.4–0.8s | 内侧短步、外侧长步，头向新方向探；甲始终闭合 | 回 walk，足点不可绕根滑转 |
| `touch_pause` 轻触 | 0.75–1.2s | 停步、触角微收、前身下沉约体高 3%，再探头 | 保留所处步相；至少稳定 0.2s 再继续 |
| `takeoff` 叶间短飞／邀请飞向可落手指 | 0.65–0.95s | 先停稳→甲片打开 50–65°→展开膜翅→加速扇翅→离面 | 有足点释放事件，未离地取消则按相反顺序收翅合甲 |
| `flight` 短距离航路 | 0.08–0.12s 翅循环，航段 0.7–2s | 后翅可视 9–12Hz，甲片保持开启、腿向后收；避免整个壳体震动 | 飞行转向用 5–12° 侧倾；目标稳定后 land |
| `land` 叶／花／指尖 | 0.75–1.1s | 伸足与减速→接触→膜翅停拍并收回→甲片最后闭合 | 隐藏膜翅仅允许完全被甲片遮住后；回 idle/hand_perch |
| `hand_perch` 爬／飞到手指 | 2.5–5s 循环 | 小范围探触角；手上行走最多半个体长，不向指尖边缘持续爬 | 可走回有连续连接的叶面；否则先 takeoff 再回栖息地 |

### 独角仙（9 种）

| 动作 / 触发 | 时长与循环 | 姿态要点 | 退出与衔接 |
| --- | --- | --- | --- |
| `idle_heavy` 树皮／宽叶停留 | 3–5s 循环，停 4–12s | 甲壳稳定，触角缓动；腹部呼吸幅度 ≤体高 1%，保持重量感 | 探前足后进入慢步 |
| `crawl` 树枝预设路线 | 步周期 0.8–1.2s | 比瓢虫长支撑期；前足探落点，中后足推动，胸部小幅跟随法线 | 落稳后停，角不穿入前方枝叶 |
| `turn` 树枝弯曲／观察手部 | 0.8–1.35s | 分 2–3 小步转身，头甲与角先转 3–6°；限制狭窄树枝上的急转 | 无足点则回退半步或换路线，不能凭空扭转 |
| `touch_observe` 轻触 | 1.1–1.65s | 停住→触角朝来源→前身抬 5–9°→缓慢落回；角随头 | 不抬离所有支撑足，回 idle 再恢复 crawl |
| `takeoff` 换栖息点／受邀／离手 | 1.0–1.4s | 蓄势较慢，甲片 45–60°，后翅展开；先加强拍翅再抬身，腿最后离面 | 松脚后进入 flight，未离地可收翅取消 |
| `flight` 叶花或手指航路 | 0.08–0.12s 翅循环，航段 1–3s | 后翅可视 9–12Hz，身体前倾 6–12°，甲壳稳定、足部后收 | 先沿宽弧降速，不能贴近指尖后急停 |
| `bank_turn` 航路改变 | 0.6–1.1s 可叠加 | 侧倾 4–9°，转弯半径大于蝴蝶，角尖计入净空 | 入 land 前侧倾归零 |
| `land` 宽叶／花托／手指 | 0.95–1.4s | 先后足／中足建立稳定支撑，再落前足；膜翅停拍收回，甲片最后合拢 | 表面可用面积不足则改宽叶或掌心；不能让六足横跨狭窄指尖悬空 |
| `hand_perch` 可承载手指或掌心 | 2.5–4.5s | 身体低稳，前足短探，角远离手面；固定模型尺寸 | 经 takeoff 离开；当前 GardenRuntime 尚需将独角仙加入邀请资格 |

### 毛毛虫（7 种）

| 动作 / 触发 | 时长与循环 | 姿态要点 | 退出与衔接 |
| --- | --- | --- | --- |
| `idle_breathe` 叶面休息 | 3–5s 循环，停 3–9s | 轻微体节体积变化 ≤2%，腹足固定，头部微探 | 下一蠕动从现有相位继续 |
| `crawl_contract` 爬行收缩半周期 | 0.65–0.9s，和伸展配对循环 | 从前向后传播可见压缩波，前端建立支撑后后体跟进；相邻节间距连贯 | 后部腹足重新固定，进入 crawl_extend |
| `crawl_extend` 爬行伸展半周期 | 0.75–1.05s | 后体支撑，前体向路径延伸；约 60–70% 腹足保持接触，禁止全体同时漂起 | 新前足点确认后进入下一收缩或 idle |
| `turn_follow` 叶脉曲线变向 | 1.2–2.0s | 头先沿新切线，后节沿已走过的中心线跟随，曲率逐节传播 | 不逐节复制头部朝向；尾巴通过弯道后完成 |
| `head_explore` 停步探索 | 1.4–2.2s | 前 1–2 节抬 10–18°，头轻转，后部腹足锁定；分件后端限制角度不露内层 | 先放回前足再继续爬，不落头穿叶 |
| `touch_recoil` 轻触 | 1.1–1.7s | 0.15–0.25s 前体轻缩 6–8%，短停 0.2s，0.7–1.1s 缓慢探出；颜色节序不改变 | 多次触碰只刷新短停，不叠加压缩；回 idle 后再爬 |
| `edge_hide` 靠近叶缘 | 2.5–4s 单次 | 逐节绕过有厚度的叶缘，沿同一连续表面从正面走到背面，足点依次换面 | 所有节均遵循表面后才能进入叶背 idle；没有背面路线时停边探索，不能整体 roll=180° |

毛虫不飞，不因手部邀请直接跳到手上；只有连续可达的叶→手表面路径才允许以后扩展爬行转移。

## 4. 叶片、花朵与手的接触约束

每个落点提供 `surfaceId`、局部位置、法线、切线、可站立半径、表面速度及有效性。花瓣只用可站立区；软花瓣边缘不作为独角仙默认落点。叶片和树枝可以用预设曲面／路线求点与法线，不要求首版引入物理网格碰撞。

模型提供 `support_center`（足底支持中心）、`belly_clearance`、六足 `foot_*`／毛虫腹足锚、`head_tip`／`horn_tip` 和包围半径。这些是 rig 元数据中的局部点，不能用模型 root 当足底点。根位置由接触锚和目标表面决定：先求根旋转 R，再令 `rootPosition = surfacePoint - R * support_center + clearance * normal`，并按实际模型 scale 一致换算。

手部锚优先取末节指骨和指尖，手指方向为两者连线、表面法线来自手掌方向并保持符号连续；仅有当前 `HandPoint` 三维位置不够表达稳定手指接触，需补 `HandAnchor(position, normal, tangent, velocity, confidence)`。独角仙的支撑宽度超出指尖有效区域时改停掌心／近处宽叶，不能缩小到肉眼突然变号。

1. **接近：** 手稳定约 0.65s、速度 <0.08m/s 后邀请；预留落点法线上方 1–2 个体高的 approach 点。末段轨迹同时约束位置和速度，落地不发生瞬间吸附。
2. **接触：** 表面可用时降低末段速度，触地阈值初值为足尖距面 1–2mm（近手尺寸）；记录足点的表面局部坐标。法线变化平滑，手部位置与法线使用同一滤波结果，不让虫与手相位不同步。
3. **停留：** stance 足点随表面刚体变换，身体与足的相对误差由两段腿 IK 吸收；swing 足走有抬高的弧线，落脚后再锁定。固定足不是固定世界点，否则移动叶片和手会从脚下滑走。
4. **移手：** 慢速跟随，快速移手初值 >0.5m/s 或目标跳变 >5cm 触发离开。短暂追踪丢失容忍约 0.15s，只保持最后有效锚；随后从最后有效姿态起飞回已知栖息点，不把失效坐标当成原点。
5. **取消：** 追踪失效优先安全离手，禁止为了播放完落地动画继续向旧指尖飞。仍在空中则改航路；已接触则解锁足点、连续起飞。

这些距离／速度是实施初值，最终需按真实昆虫缩放和真机手追踪抖动调整。手上与空中保持同一实例的固定 scale；当前 `hovering` 导致 `.74→.44` 的即时大小变化需要删除或在明确的入场镜头中一次性定标。

### 避免脚滑、穿叶与甲翅互穿

- **路径推进按支持状态和速度，而不是全局正弦时间。** 步相推进量由实际走过距离／步幅决定，触碰暂停同时停路径。当前只停 `animationTime`、位置仍追逐 natural target 会脚滑。
- **至少一组足保持接触。** 用脚底支持面求 body up；步幅超出可达范围先换脚，不能拉长腿。接触 IK 用自写解析两段求解和角度限制，不宣称 SDK 自带 IK。
- **当前整腿降级：** 只允许小步、缓慢转向和短移动；记录并验收足端误差。超过误差预算时缩短步幅／回静止，正式近观目标仍需分腿。不得把腿根正弦摆动作为无脚滑验收的替代。
- **净空：** 腹底及角尖采样点距表面大于各自 clearance；朝向用曲面切线与法线组成，毛虫逐节采样。翅扫掠体碰到叶片时先抬高胸部或改选落点，不能仅关闭碰撞。
- **起落顺序：** 甲片打开到安全角才展开膜翅；膜翅收进甲下再合甲。只有单片膜翅时先旋回甲下再隐藏；可见折叠要求额外 fold 关节／网格，不用突然缩放冒充折叠。
- **叶背：** 路线包含叶缘厚度和法线旋转；叶正背面与边缘属于同一表面连通图。现有整体翻滚路径不能保证体节及足部不穿叶。

## 5. 调度、节奏与取消优先级

单实例由一个控制器拥有 root 和 part 姿态；路径更新、接触修正和动作按固定顺序执行：`行为选择 → 路径/接触锚 → 动作采样 → 足点约束 → 姿态写入`。不要让 `NaturalMotion`、动画资源和触碰回调同时写同一个 Transform。

状态最少分为 `GROUNDED / TAKING_OFF / FLYING / LANDING / HAND_PERCHED / LEAVING`；毛虫使用 grounded 内子动作。跨状态事件为 `lift_off`、`touch_down`、`wings_stowed`、`all_feet_planted`；这些事件由归一化时间跨阈值触发一次，不比较浮点相等。

| 优先级（高→低） | 处理方式 |
| --- | --- |
| 销毁／退出 Stage／应用暂停 | 停时钟、清监听与手锚，停止并关闭播放控制器；不得后台补跑一长段 delta |
| 跟踪失效／快速移手／落点无效 | 从当前姿态连续离开或改道，可中止 land/hand_perch |
| 用户删除／容量退场 | 禁止新邀请；手上先解锁离手，再退场；离地后继续正常飞行姿态 |
| 触碰反应 | 打断地面日常动作；空中只做小幅方向／触角回应，不突然合翅坠落 |
| 手部邀请 | 仅一只取得邀请锁；未离地被取消则收翅，已离地则返回可落栖息点 |
| 日常活动与 idle | 当前动作在落脚／一段拍翅边界结束；可用短过渡合成 |

取消过渡从已采样的当前姿态开始；保存脚点、拍翅相位与速度，不能重新从 bind pose 播放。所有日常动作以实例 ID 派生相位、时长和小幅振幅；自然变化每次动作边界取样，不每帧噪声。头／触角叠加层幅度小且不得覆盖着地姿态。全场最多 1 只进入手部互动，其余错开休息和移动，避免十只同时拍翅或起飞。

近处以场景帧率写姿态；远处可降低小腿／触角更新频率，但 root 路径连续。优先降低远处动作细节，不改近手昆虫质量。CPU/GPU 消耗必须在满员 10 只真机中测量，当前文档没有性能通过结论。

## 6. 交给主线的最小接口与现有差距

无需立刻建立通用动画框架；增加一个按物种配置的控制器即可：

```text
InsectMotionInput:
  delta, species, desiredSpeed, routeSample, contactAnchor?, touchEvent,
  invitationRequested, retiring, trackingValid
InsectMotionOutput:
  rootPose, partLocalPoses, visibleParts, footContacts,
  locomotionState, events, retirementReady
RigDescription:
  forwardAxis, restParts, hingeAxes, limits, supportCenter, footAnchors
```

控制器可保留平铺 Entity：先在 CPU 求逻辑父子变换，再一次写各 part 的根相对变换；或者建真实父子层级并统一改 pivot。两者选一种，不混用。每次姿态从 rest pose + 当前动作求值，避免 frame-to-frame 累积误差；缺少足部锚时明确只启用降级步态。

当前应优先修正的具体问题：

1. `ModelLibrary.animate(time,flying,open,reaction)` 的布尔参数不足以表示预开甲、起飞、接触和收翅；扩展为上面的状态／姿态输入。甲片动画需要显式分支，目前只处理 `wing_` 和 `flight_wing`。
2. `GardenRuntime` 只让蝴蝶与邻近瓢虫受邀，独角仙新增资格、较宽支持面和完整离手路径；flying 状态由控制器统一给出。
3. `NaturalMotion` 的 heading 翻转和毛虫整身 roll 180° 改成带切线、法线、速度、表面 ID 的连续路径；停止触碰反应时也停止路线推进。
4. `head/eyes/antenna/horn`、毛虫腹足必须跟随所属逻辑节点；当前所有 part 平铺在 root，单独摆头会让附属件留在原地。
5. 预览使用同一动作配置但固定安全栖息锚，支持温和 idle／展开观察；作品纹理更新不重建控制器、不重置行为相位。

可选 GLB 后端真机探针流程：`context.assets.open("rig_probe.glb").use { Entity.loadSuspend(it, ModelFormat.GLTF) }` → `findSkinnedMeshEntity()` → 枚举 `getAnimationResources()` 的真实名称 → `playAnimation(resource, AnimationPlayConfig(...))` → 读取 controller.duration/time，测试 pause/resume/speed 和过渡。预览与 Stage 都需测试，并确认按名称找到的材质能更新用户纹理。不要硬编码第一段 animation 为 idle。SDK 暴露 CROSSFADE/STOP_AND_CROSSFADE 和 blend 层参数，混合骨骼覆盖的具体表现仍待真机确认。

## 7. 证据与验收

初始设计轮仅写文档和独立探针，未修改运行时代码或模型 Agent 的产物；后续已授权的程序动作实施记录见第 8 节。

- [Blender 制作脚本](../assets-src/v2/animation-probe/create_probe.py)、[往返验证脚本](../assets-src/v2/animation-probe/verify_probe.py)、[可编辑骨架场景](../assets-src/v2/animation-probe/rig_probe.blend)、[GLB](../assets-src/v2/animation-probe/rig_probe.glb)。探针是绿色弯管，不是正式毛虫。
- [制作报告](../assets-src/v2/animation-probe/authoring-report.json)、[往返报告](../assets-src/v2/animation-probe/roundtrip-report.json)，验证后者 `status=passed`、`pico_runtime_tested=false`。导入保留 3 根骨、3 段动作及归一化权重；不同帧最大顶点位移见报告。
- [静止帧](../assets-src/v2/animation-probe/pose_01.png)、[弯曲帧](../assets-src/v2/animation-probe/pose_13.png) 已查看，关节处连续、没有分离；不是正式材质验收图。

后续验收逐项记录真实画面和测量结果：

1. 每种昆虫逐个触发本表动作，连续录制进入／循环／退出；各至少 5 个可辨动作，三类飞虫完整执行叶／花／手指起落。
2. 左右不对称测试纹理在动作前后保持方向、节序、留白和接缝；甲片与翅背面有正确图案，不通过换材质掩盖姿态问题。
3. 近手视距下足点锁定：目标足端相对表面误差初值 ≤1.5mm，腹／角／翼扫掠不穿面；整腿降级不通过则拆腿后再验。
4. 交错测试触碰、邀请取消、快速移手、追踪丢失、容量退场；无 root 瞬移、突然缩放、卡在半开甲和无限循环事件。
5. 满员 10 只、场景和音频同时运行，测帧耗时、内存、动作资源释放；重复进出 Stage 后无残留控制器。Blender 导出成功不代替此项。

## 8. 程序动作实施记录

已新增纯 Kotlin `garden/InsectAnimationController.kt`。三类飞虫可输出 IDLE/WALK/TURN/TOUCH/TAKEOFF/FLIGHT/LAND/PERCH；毛虫可输出 IDLE/CRAWL/TURN/EXPLORE/RECOIL，忽略飞行请求。控制器提供渐进的 `flightBlend`、`shellOpen`、有限触碰包络及独立实例相位。触碰暂停步相；持续触碰值不会不断重启动作；取消起飞／落地从当前权重衔接；异常 delta 不污染时钟。

`ModelLibrary.InsectModel` 新增 `animate(InsectAnimationFrame)`，保留原有 `animate(time,flying,open,reaction)` 预览入口。姿态从 rest pivot 每帧计算：左右甲片先开，膜翅随后可见并扇动；左右六足用交替三足相位；头、眼、角和触角末端成组跟随；毛虫将收缩限制在 6%，步行体节位移约毫米级，探索抬头最多 6mm（模型原始尺度）。现有 v2 加载、纹理与材质部分未因动画更改。

v1 资产显式进入 `LegacyInsectAnimation` 兼容分支，两个 animate 入口均按 `v2/` 资产前缀分流。旧网格已将部件位置烘焙入顶点，保持旧版简单姿态：`flight_wing-1/flight_wing1` 按数值后缀镜像；独角仙不绕不存在的 neck 转动 head/horn；毛虫 `foot_i_*` 跟随第 i 节，眼睛和高光跟随第 6 节。资产加载路径与作品版本选择不变。

主线集成约定（控制器每只实例只建立一次）：

```kotlin
val animation = InsectAnimationController(species, seed)
// 每帧：turning ∈ [-1,1]；flying 是期望飞行；onHand 表示落手意图／接触。
val frame = animation.update(deltaSeconds, moving = moving, turning = turn,
    flying = wantsFlight, onHand = onHand, reaction = reaction,
    retiring = leaving, speedFactor = speedRatio)
model.animate(frame)
// root 世界路径使用 frame.action/progress/flightBlend 衔接，仍由 GardenRuntime 控制。
```

验证命令：`scripts/verify_animation.ps1 -Runtime`。纯 Kotlin JUnit 覆盖动作顺序、取消连续性、触碰优先级、重触发、防飞行、退场、相位和时间边界；额外将 ModelLibrary 与控制器对 Android 35、本地 PICO core 和 foundation 6.1.0 编译，未调用 Gradle。

仍未实现两段腿接触 IK、毛虫连续蒙皮和真实曲面脚锁；膜翅可见性为受甲片遮挡约束的分件降级，不是完整折翼骨架。世界路径／手锚／音频属于主线独立修改。真机接触误差、甲翅净空及满员性能仍需按第 7 节验收。
