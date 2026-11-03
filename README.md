# Hex Mosaic · 六边形点阵风格化

在线体验：https://zer0tsu.github.io/hex-mosaic/

把任意图片转成「六边形密排点阵」风格插画：深色底 + 浅色点，靠点的大小（或深浅）还原明暗。适合做头像、海报、LED 点阵屏效果图。

包含两个实现，共用同一套算法：

| 版本 | 文件 | 说明 |
| --- | --- | --- |
| 网页版 | `index.html` | 纯前端 Canvas 2D，零依赖零构建，双击即可用 |
| 命令行 | `hex_dot_art.py` | Python + Pillow，适合批量处理与高分辨率出图 |

## 效果特点

- **抠图**：自动（透明通道优先，否则按四角背景色漫水填充）/ 色键 / alpha / 不抠，并可选挖掉角色内部缝隙（发丝间隙、腋下透出的底色）
- **点阵**：六边形密堆积，点间距、圆角、六边形↔圆形可调
- **明暗映射**：越亮越大或越暗越大；也可切到「点深浅」模式，所有点等大、用明暗表现层次
- **配色**：自定义点色与底色、内置配色预设、输出透明背景 PNG
- **导出**：1×–4× 倍率，网页版支持拖入 / 粘贴 / 导出 PNG

## 网页版用法

直接用浏览器打开 `index.html`（或访问部署好的在线地址）：

1. 拖入图片、点击「打开图片」，或按 `Ctrl+V` 粘贴剪贴板图片
2. 左侧面板调参：抠图 → 网格 → 形状 → 明暗映射 → 颜色
3. 「按住看原图」对比，`Ctrl+S` 或点「导出 PNG」保存

参数会自动保存在浏览器 localStorage，刷新不丢。

## 命令行用法

```bash
pip install pillow
python hex_dot_art.py 角色_透明.png -o out/art.png
python hex_dot_art.py 参考图.png -o out/art.png --key "#ff00ff" --width 2000
python hex_dot_art.py 参考图.png -o out/art.png --cell 9 --gamma 0.85 --tone dark
python hex_dot_art.py 参考图.png -o out/art.png --transparent
```

完整参数见 `python hex_dot_art.py --help`。

## 目录结构

```
.
├── index.html                  # 网页版（单文件，零依赖）
├── hex_dot_art.py              # 命令行版
├── index.legacy.html           # 早期版本，保留作对比
├── samples/                    # 示例输入图
├── scripts/                    # 构建 / 预览 / 部署脚本
├── .github/workflows/pages.yml # GitHub Pages 自动部署
└── DEPLOY.md                   # 部署文档
```

## 部署

见 [DEPLOY.md](DEPLOY.md)。

## 许可证

未指定。如需开源请自行补充 LICENSE。
