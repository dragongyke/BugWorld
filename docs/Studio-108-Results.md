# BugWorld 1.0.8 · 顶部导航与画具面板

## 用户反馈与修改

- **四个昆虫一起高亮、蝴蝶误开选择面板**：1.0.7 为缩短导航，把四个可点击控件嵌套进一个原生 TabBar item，外层点击还绑定了「更多」。现改为每个昆虫一个原生 item，使用该项原生 Hover 与点击；仅当前画纸保持选中状态。四种昆虫都直接切换画纸，超过四种后才出现独立「更多」入口。
- **保持 TopBar 紧凑**：Logo 96 × 24 dp、昆虫图标 40 dp，减少原生等宽项目受品牌/作品册内容撑宽的影响。
- **画具右侧灰条**：SDK 6.1.0 的 Subwindow 固定宽 360 dp，旧内容宽 320 dp，露出系统材质。移除内容宽度限制，铺满原生容器。
- **画具朝向用户**：保留随主窗口移动的右侧 Subwindow，以靠近画板的左边为轴，向内旋转 25°。使用原生 `Rotation3D`，输入面跟随真实空间变换。

用户已确认 1.0.7 的凝视反馈增强、画具能跟随主画板；本版继续修正上述细节。

## 验证

- **用户真机验收（2026-10-19）**：针对昆虫各自高亮、灰条消失及画具向内倾斜的体验，用户确认「都正常，角度合适」。上述三项已通过；此确认不包含 Stage 返回。
- 105 项单元测试通过；Lint 0 错误、33 警告；APK 构建成功。
- 新增真机语义回归脚本 `scripts/verify_studio_chrome.py`：修改前在 1.0.7 失败，发现昆虫有两个点击祖先；1.0.8 通过，四个昆虫各有唯一、互不共享的点击入口。
- 真机依次点击独角仙、瓢虫、毛毛虫、蝴蝶，画板标题均正确，无「选择画纸」弹层。
- 画具内容与原生窗口边界均为 `(0, 0)–(720, 1680)` 像素，内容已覆盖完整宽高。
- 扩展回归通过了 TopBar 宽度检查（画板宽度的 76.57%）和新画纸确认/取消。随后在预览期间等不到新画纸弹窗；检查发现应用已进入 Stage，脚本当时尚未执行进入 Stage 的步骤，无法确认这次状态变化来自哪里，因此记为未完成并停止自动操作。Stage 返回仍未验收，不把本次中断当作该流程通过。
- 扩展回归记录见 [设备记录](Studio-108-Device-Verification.json)；已通过的专项记录见 [导航与画具](Studio-108-Chrome-Verification.json)。凝视光效、灰边视觉及空间角度舒适度由上述用户真机反馈确认，不以自动语义操作代替视觉验收。
- 首次 CLI 安装尝试使用了不支持的 `--apk` 参数，未安装；随后按 CLI 帮助改为位置参数，覆盖安装和启动成功。作品册数据保留。

## 交付与依据

- APK：`deliverables/BugWorld-1.0.8.apk`，175,632,517 字节，versionCode 8，SDK 6.1.0。
- SHA-256：`430a985911334b6848102a19d65ee8b301e7c7ab20c13795e0210fc96edb74a1`；与设备已安装 base.apk 一致。
- 分支：`codex/bugworld-v1`。本版未修改模型、场景或画纸资产。
- [CLI、时间及 Token 统计](Implementation-Metrics.md) · [本轮用量快照](Studio-108-Usage.json)。
- API 核对本地 6.1.0 AAR 字节码；公开参考：[TabBar item](https://developer.picoxr.com/spatial-api/0.13.3/spatialui/design/com.pico.spatial.ui.design.windows/-tab-bar-scope/item.html)、[Subwindow 原生旋转示例](https://developer-cn.picoxr.com/spatial-api/6.1.9/spatialui/design/com.pico.spatial.ui.design.windows/-subwindow.html)。网页版本与项目 SDK 不同，实际签名以本地编译验证为准。
