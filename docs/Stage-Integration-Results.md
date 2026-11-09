# 1.0.6 集成结果

本版包含 Shared Space 预览优化，以及独立对话 **BugWorld · Stage 场景性能与水面优化** 产出的场景候选。APK：`deliverables/BugWorld-1.0.6.apk`。

## 实际改动

- 预览提前准备当前昆虫；收起后复用，未变化的作品不重复上传纹理。手势拖动旋转，直接触碰播放对应动画，移除模型操控按钮。
- Stage 从 740,784 降至 494,775 三角面；glTF primitive 从 150 降至 49，贴图完整 mip 的 RGBA8 估算从 224 降至 144 MiB。**这些不是设备 FPS / Draw Call / 显存测量。**
- 两根倒木分别下移 34 cm、19 cm，与水面接触；同步调整苔藓、模型路径与 Kotlin 接触路线。
- 水面由 57,800 降至 2,048 三角面，改为宽缓起伏和细法线，使用匹配新场景的反射探针、粗糙度 0.17 / 法线强度 0.65。反射仍为静态探针，无动态昆虫倒影和真实平面视差。
- 保留近处倒木、两片路线荷叶的原表面；四种昆虫模型、动画、画纸、UI 图标保持批准版本。

## 一致性与验证

运行模型、`environment/garden-routes.json`、Kotlin 路线、反射探针和水面参数整体接入。派生身份在 `assets-src/stage-optimized/manifest.json`；批准原件与原批准清单保持锁定。原版 `--sync` 被阻止，避免无意恢复原模型而留下新路线。

- **99 项单测通过**，0 失败/错误/跳过；Lint **0 错误、28 警告**；APK 构建通过。
- APK 的 37 个运行资产逐文件匹配，20 个昆虫动画片段保留，无旧版资产目录。
- 28 项批准资产身份检查与 3 项派生运行资产检查通过；错误的派生指纹会被拒绝。
- Kotlin/JSON 清单散列统一 LF，GLB/KTX 使用精确字节，避免 Git 换行转换误报。
- 渲染、几何与路线证据保留在 `assets-src/stage-optimized/`；可重建脚本和完整分析见 [Stage 报告](Stage-Optimization-Metrics.md)。真实 GLB 的 Blender 渲染仅供资产对照，不等于头显效果。

结果：[构建与测试](Stage-Integration-Validation.json)、[APK 资产校验](Stage-Runtime-Verification.json)。时长、Token、PICO CLI 分别记录并合并一次，见 [Implementation-Metrics.md](Implementation-Metrics.md)。

## 待真机确认

设备枚举为空，尚未安装 1.0.6。加载速度改善、手势命中、画纸输入透传、材质观感、MASK 苔藓边缘、转头抖动和黑边均待设备验证。运行后可采集 `BugWorldPreview`、`BugWorldModels`、`BugWorldStagePerf` 日志；应用回调节奏不能当作合成器 FPS。

验证建议：同刷新率、同视角，分别放置 0 / 1 / 10 只昆虫，重复冷启动、进出花园、左右转头和近看水面/树皮。按 [Stage 报告](Stage-Optimization-Metrics.md) 的单变量检查定位剩余 CPU/GPU 开销，再决定下一轮优化。
