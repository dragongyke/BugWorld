# BugWorld 1.0.7 · 画板与空间交互修复

## 行为

1. **画板输入**：画纸 UI 作为 SpatialView 的原生 AttachmentPanel，与昆虫共用一套空间命中关系。移除覆盖整个 Compose 画板的独立预览层。预览仍只响应昆虫碰撞体。
2. **新会话**：冷启动、用户明确关闭画板后重新打开，显示空白画纸；历史草稿不自动回填。作品册「继续画」显式恢复原图及编辑 ID。Stage 返回及普通 Activity 重建不重置画纸。
3. **快速切换**：四张画纸预备后切换内存引用；同次会话保留笔迹、撤销和作品来源。纸纹复用；PNG 编码放后台，不再在切换路径保存、读盘、解码及重建纸纹。预览隐藏时不生成新贴图，快速切换时延迟模型预热。
4. **画具跟随**：使用 SDK 原生 `Subwindow(placement=Right)`，依附主窗口；取消独立画具 WindowContainer。第一次候选版采用 SpatialView 右侧 AttachmentPanel，用户反馈不可见，已替换为 SDK 专用侧边 augment。作品册保持独立窗口。
5. **紧凑 TopBar**：继续使用原生 TabBar，将四个昆虫图标放在同一选择区，避免 SDK 等宽布局将 Logo 宽度重复分配给每个图标。超过四种时显示三种快捷图标＋「更多」网格，不继续加宽。
6. **凝视反馈**：共用 HoverSurface，原生 `spatialHoverEffect` 与分组响应层负责 4.5% 放大、明显底色、3 dp 紫色描边；按下另有反馈。覆盖操作按钮、图标、昆虫、画具、颜色、对称开关、画纸选择及作品卡片。禁用项不高亮。凝视效果由系统进程处理，未读取或推断用户凝视状态。

补充修正：画具撤销/重做显式观察笔迹版本；画板附件使用内容测量应对窗口改尺寸；Stage 退出等待原生销毁信号，超时后若信号迟到则再恢复仍打开的窗口，避免提前 restore 后仍被系统收起。

## 验证与边界

- 最终构建：105 项单元测试通过；Lint 0 错误、33 警告；APK 成功生成。
- 新增 6 项画纸会话测试，覆盖启动空白、缓存切换与撤销、显式编辑、删除隐藏作品 ID、新画纸和重新打开；重新打开测试先失败再修正通过。
- 资产校验：28 项原始资产、3 项 Stage 派生资产及 20 个原生动画一致；APK 37 个运行资产，旧运行资产不存在。Stage 美术没有改动。
- 初步候选包：用户明确确认画板按钮可用。真机语义动作验证了新画纸确认/取消、预览显隐、四物种切换、作品册开关；日志确认 Stage 完整准备。Stage 返回暴露恢复时序问题，已进一步修正。
- 真机四次切换的状态更新为 370–547 微秒；不含合成器提交和显示，**不能据此声称满帧或零卡顿**。
- 最终包已覆盖安装，作品册数据保留。最终整套设备脚本因头显休眠未完成，用户选择稍后验证；右侧 Subwindow 可见性/随动、凝视高亮强度、实际手指命中及 Stage 返回的最终结果仍待头显确认。系统截屏接口返回 Capturing failed，没有截图证明。
- 自动脚本 `scripts/verify_studio_device.py --stage` 使用 ROM 的 `uiautomator spatial`，只执行语义操作，不冒充手指/凝视追踪。需要保持头显唤醒；脚本不保存或删除作品。

## 交付

- `deliverables/BugWorld-1.0.7.apk`：175,957,956 字节。
- SHA-256：`ce1d6c49825a4cb03ce1c369e7758eae99ae258681a53e5d7289b419d16655c9`。
- 包名 `com.bugworld.app`，versionCode 7，SDK 6.1.0；功能分支 `codex/bugworld-v1`。
- 资产证据：[Studio-107-Runtime-Verification.json](Studio-107-Runtime-Verification.json)。
- 时间、CLI、Token：[Implementation-Metrics.md](Implementation-Metrics.md)、[Studio-107-Usage.json](Studio-107-Usage.json)。

## SDK 依据

API 签名同时核对本地 6.1.0 AAR；公开网页版本为参考：

- [Subwindow](https://developer.picoxr.com/spatial-api/0.13.3/spatialui/design/com.pico.spatial.ui.design.windows/-subwindow.html)：主窗口侧边组件及跟随配置。
- [Spatial Hover](https://developer.picoxr.com/spatial-api/6.1.9/spatialui/foundation/com.pico.spatial.ui.foundation.hover/spatial-hover-effect.html)：系统进程中的指向/凝视效果，与普通 hoverable 不同。
