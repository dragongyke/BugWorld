# BugWorld v3 · 品牌、工具图标与实际资产排版

这是资产评审候选，不是 SDK 运行截图，也不表示窗口、TabBar 或交互已在应用中实现。应用代码和根审阅页均未修改。

## 查看实际效果

- `boards/asset-layout-review.svg` / `.png`：1920×1280。使用已交付的四种昆虫图标与四张画纸 SVG，排列中央画纸、右侧画具、左侧作品册；顶部明确标为“TabBar · 依附画纸的昆虫导航”，不作为第四个独立窗口。
- `boards/logo-and-tools-contact.svg` / `.png`：1600×850。品牌组合以及十个工具图标；图标分别按 48 与 64 像素放置，可检查真实尺寸下的轮廓。

排版使用暖白、浅紫和明确留白，依据 `docs/visual-redesign/2026-10-08/04-shared-space-multiwindow-v2.png`。概念图只作为设计依据；所有产品资产均是新生成的 SVG 路径，没有概念图像素、外部图片嵌入或模拟的 SDK 截图。

## 可交付资产

| 文件 | 内容 |
| --- | --- |
| `brand/bugworld-logo.svg` | 369×72 viewBox；实际蝴蝶图标 + BugWorld 字标；字标已转为完整矢量轮廓，不依赖字体安装 |
| `brand/bugworld-logo.png` | 738×144，透明 RGBA，便于直接查看和导入 |
| `brand/bugworld-mark.svg` | 64×64，复用自己手绘的蝴蝶导航图标 |
| `icons/crayon.svg` | 蜡笔 |
| `icons/fill.svg` | 填色桶与滴落标记 |
| `icons/eraser.svg` | 橡皮 |
| `icons/album.svg` | 打开的画册 |
| `icons/save.svg` | 保存箭头与托盘 |
| `icons/leaf.svg` | 叶子 / 送到自然 |
| `icons/undo.svg` / `redo.svg` | 撤销 / 重做 |
| `icons/preview.svg` | 预览三角 |
| `icons/close.svg` | 关闭 |
| `icons/*-48.png` / `*-64.png` | 十个工具图标的透明目标尺寸栅格，共 20 张 |
| `manifest.json` | 颜色、尺寸、真实输入资产和候选状态 |

工具图标为 24×24 viewBox，主描边 1.65，采用圆角端点和转角；辅助线按需要收细。SVG 可以无损放大，48/64 PNG 并非将概念图裁剪后缩放。

品牌字标沿用批准图的衬线气质，使用系统 Georgia Bold 的字形轮廓组合；通过本地 Windows GDI 读取并转成路径，没有复制或打包字体文件。品牌蝴蝶来自 `assets-src/v3-review/lineart/icons/butterfly.svg`。

排版板中的中文保留为可编辑 SVG 文本，字体声明为 `Microsoft YaHei, sans-serif`；PNG 是本机实际渲染结果，用于避免审阅环境字体替换引起排版差异。Logo 与单独工具 SVG 均只依赖路径。

## 真实输入与示意范围

导航条使用 `assets-src/v3-review/lineart/icons/` 下四个独立图标。中央画纸和作品册使用 `assets-src/v3-review/lineart/sheets/` 下实际轮廓 SVG。窗口底色、背景渐变、纸张细纤维和按钮排版为本次可编辑 SVG 示意；不是实测的玻璃材质、蜡笔算法、设备光照或空间定位。

“草稿已保存”、时间和选中状态是排版样例。图中没有假装实际运行的 3D 预览；模型和场景应查看各自的资产渲染与验收材料。

## 再生成与自查

唯一源脚本：`scripts/assets_v3_ui.py`。脚本只写本目录，读取已经存在的线稿资产。运行：

```powershell
& 'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/assets_v3_ui.py
```

使用系统 GDI、标准 Python 与捆绑 Node sharp/librsvg。换环境时可以设置 `BUGWORLD_NODE` 和 `BUGWORLD_SHARP`；字标再生需 Windows Georgia，但已输出的 Logo SVG 不需要。

已自看实际排版 PNG、Logo PNG 和工具图标联系表，检查字形、间距、标记、轮廓与透明底。生成时检查全部 SVG 可解析且没有 `<image>` 栅格嵌入；工具和品牌 PNG 检查了尺寸与透明通道。共 39 个交付/说明文件。尚待用户最终审核，不作 SDK 集成或真机效果完成声明。
