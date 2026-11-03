#!/usr/bin/env python3
"""六边形点阵风格化器。

把一张图渲染成「深色纯色底 + 浅色点」的点阵画。

三种抠图模式，自动选择，也可以用 --key 手动指定：
  * alpha   输入是透明背景 PNG → 直接用 alpha 当角色 mask，像素级精确，最省事最准；
  * key     用 --key "#ff00ff" 指定一个和角色明显不冲突的纯色背景 → 按色差抠图，
            不需要漫水填充，也不怕白衣服和底色撞色；
  * flood   普通不透明图 → 从边框做连通域漫水填充猜背景(兜底方案，最不保险)。

其余规则：
  * 画不画点完全由 mask 决定，不再靠亮度阈值 —— 所以角色的白皮肤、白衣服即使和背景
    同色也不会被丢掉，只会按 --tone 的规则画成对应大小的点；
  * flood 模式下，被角色包住的纯背景色区域(头发之间的缝、腋下/裙摆透出的底色)
    会额外当作「洞」挖空，用更严的 --hole-tol 判定，避免把同样发白的衣服误挖；
  * --white-hole 是给 key 模式的补挖开关，默认关闭。实测风险很大：角色自己的白色衣服、
    高光会和「漏抠的发丝缝」长得一样白，开了很容易把衣服挖出空洞，非必要别用；
  * 默认 --tone light：越亮的地方点越大（白色衣服=大点，暗部/线稿=小点），
    换成 --tone dark 则反过来（越暗点越大）；
  * 六边形密排网格上每个格点画一个实心圆点，半径由明暗映射得到。

用法示例:
    python hex_dot_art.py 角色_透明.png -o out/art.png          # 透明图，最准
    python hex_dot_art.py 角色_洋红底.png -o out/art.png --key "#ff00ff"
    python hex_dot_art.py 参考图.png -o out/art.png --cell 9 --gamma 0.85 --width 2000
    python hex_dot_art.py 参考图.png -o out/art.png --tone dark     # 暗部用大点
    python hex_dot_art.py 参考图.png -o out/art.png --transparent   # 输出透明底，自己配纯色

本仓库同时是网页版（index.html，纯前端 JS 实现，无需 Python）。两边共用同一套算法：
四角中位色 + 扫描线漫水填充 / 色键 / alpha 抠图、内部缝隙挖空、0.5%~99.5% 分位色阶、
六边形密排点阵、明暗映射到点大小（或点深浅）。改动其中一边时请同步另一边。
"""

import argparse
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

try:  # 保证中文提示在各种控制台编码下都能安全输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_args():
    p = argparse.ArgumentParser(description="把图片渲染成六边形点阵风格的画")
    p.add_argument("src", help="输入图片路径")
    p.add_argument("-o", "--out", default="out/hex_dot.png", help="输出 PNG 路径")
    p.add_argument("--width", type=int, default=1600, help="输出宽度(px)，高度按比例")
    p.add_argument("--cell", type=float, default=11.0, help="点阵间距(输出 px)，越大点越稀")
    p.add_argument("--gamma", type=float, default=0.9, help="明暗映射曲线，<1 让中间调更亮")
    p.add_argument("--tone", choices=("light", "dark"), default="light",
                   help="light=越亮点越大(默认)，dark=越暗点越大")
    p.add_argument("--min-ratio", type=float, default=0.22,
                   help="前景最暗/最亮处的最小点半径，占最大半径的比例")
    p.add_argument("--cutoff", type=float, default=0.0, help="低于此映射值的格点不画(留空白)")
    p.add_argument("--mask-thresh", type=int, default=128, help="mask 采样值高于此值才算角色")
    p.add_argument("--hole-thresh", type=int, default=100, help="内部背景缝的判定阈值，越大保留越多")
    p.add_argument("--no-punch", action="store_true", help="不挖内部背景缝(头发间隙会被填实)")
    p.add_argument("--white", type=int, default=238,
                   help="仅 --no-extract 时生效：亮于此灰度视为背景，不画点")
    p.add_argument("--fg", default="#d9d9d9", help="点的颜色")
    p.add_argument("--bg", default="#1c1c1c", help="底色(纯色)")
    p.add_argument("--transparent", action="store_true", help="背景留透明，输出 RGBA")
    p.add_argument("--ss", type=int, default=2, help="超采样倍数(抗锯齿)，2 或 3")
    p.add_argument("--tol", type=int, default=26, help="外部背景色容差，越大抠得越狠")
    p.add_argument("--hole-tol", type=int, default=6,
                   help="内部缝隙的背景色容差，越小小缝挖得越干净、越不会误伤白衣服")
    p.add_argument("--key", default=None,
                   help="指定背景色(如 #ff00ff)做 chroma key 抠图，优先级高于自动判断")
    p.add_argument("--key-tol", type=int, default=40, help="chroma key 的颜色容差")
    p.add_argument("--white-hole", type=int, default=None,
                   help="【慎用】在角色内部把近白像素(色差<=N)补挖成缝。实测会把角色自己的"
                        "白色衣服/高光一起挖掉，只在抠图工具确实漏抠了发丝缝时才开，如 4")
    p.add_argument("--no-extract", action="store_true",
                   help="完全不抠图，整张图直接点阵化(需自己保证背景够暗)")
    p.add_argument("--no-autocrop", action="store_true", help="不按内容自动裁边")
    return p.parse_args()


def hex_to_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- 前景提取

def _base_color(rgb, w, h, patch=6):
    """取四角小块的中位色作为背景参考色。"""
    px = rgb.load()
    samples = []
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        for dy in range(-patch, patch + 1):
            for dx in range(-patch, patch + 1):
                x = min(w - 1, max(0, cx + dx))
                y = min(h - 1, max(0, cy + dy))
                samples.append(px[x, y])
    samples.sort(key=lambda c: c[0] + c[1] + c[2])
    return samples[len(samples) // 2]


def _flood_border(cand, w, h):
    """扫描线漫水填充：标出所有与画面边框连通的候选像素。"""
    filled = bytearray(w * h)
    stack = []
    for x in range(w):
        if cand[x]:
            stack.append((x, 0))
        if cand[(h - 1) * w + x]:
            stack.append((x, h - 1))
    for y in range(h):
        if cand[y * w]:
            stack.append((0, y))
        if cand[y * w + w - 1]:
            stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        row = y * w
        if filled[row + x] or not cand[row + x]:
            continue
        xl = x
        while xl > 0 and cand[row + xl - 1] and not filled[row + xl - 1]:
            xl -= 1
        xr = x
        while xr < w - 1 and cand[row + xr + 1] and not filled[row + xr + 1]:
            xr += 1
        for i in range(xl, xr + 1):
            filled[row + i] = 1
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                nrow = ny * w
                i = xl
                while i <= xr:
                    if cand[nrow + i] and not filled[nrow + i]:
                        stack.append((i, ny))
                        while i <= xr and cand[nrow + i]:
                            i += 1
                    i += 1
    return filled


def background_split(rgb, tol, hole_tol=None):
    """把画面分成「前景角色」和「被角色包住的背景洞」两块。

    两者都以四角参考色的容差判定为基础：与边框连通的纯色像素是外部背景，
    没连通上的纯色像素就是角色内部的缝(头发间隙、腋下/裙摆透出的底色)。

    hole_tol 用更严的容差来单独判定「内部缝」：纯背景色(差<=6)才算缝，
    偏灰的白(衣服、阴影)容差放宽也进不来，所以不会被当成缝挖掉。

    返回 (前景 mask, 洞 mask)，均为 L 模式、255 表示命中。
    """
    w, h = rgb.size
    bg = Image.new("RGB", (w, h), _base_color(rgb, w, h))
    diff = ImageChops.difference(rgb, bg).convert("L")
    cand = bytearray(diff.point(lambda v: 1 if v <= tol else 0).tobytes())
    filled = _flood_border(cand, w, h)

    if hole_tol is not None and hole_tol != tol:
        cand = bytearray(diff.point(lambda v: 1 if v <= hole_tol else 0).tobytes())
    holes = bytes(255 if (c and not f) else 0 for c, f in zip(cand, filled))
    fg = bytes(0 if f else 255 for f in filled)

    mask = Image.frombytes("L", (w, h), fg)
    holes = Image.frombytes("L", (w, h), holes)
    # 中值去噪 + 轻度羽化，避免边缘硬切
    mask = mask.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    holes = holes.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    return mask, holes


def foreground_mask(rgb, tol):
    """只要前景角色 mask 的便捷入口。"""
    return background_split(rgb, tol)[0]


def has_useful_alpha(im):
    """判断图片是否带真正有效的透明通道。"""
    if im.mode in ("RGBA", "LA"):
        return im.getchannel("A").getextrema()[0] < 250
    if im.mode == "P":
        return "transparency" in im.info
    return False


def alpha_mask(rgba):
    """用 alpha 通道当角色 mask —— 透明抠图是像素级精确的，不需要任何猜测。"""
    mask = rgba.getchannel("A")
    mask = mask.filter(ImageFilter.MedianFilter(3))
    return mask.filter(ImageFilter.GaussianBlur(0.6))


def key_mask(rgb, key, tol):
    """按指定背景色 chroma key 抠图：与 key 色差 <= tol 的像素一律算背景。

    有了明确的背景色，就不需要漫水填充，也不用担心「白衣服和底色同色」——
    只有真正等于 key 色的像素才会被当成背景。
    """
    bg = Image.new("RGB", rgb.size, key)
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda v: 0 if v <= tol else 255)
    mask = mask.filter(ImageFilter.MedianFilter(3))
    return mask.filter(ImageFilter.GaussianBlur(0.6))


def white_holes(rgb, tol, mask):
    """角色范围内残留的近白区域(抠图工具没抠掉的背景缝)。

    有些抠图工具本身也只按连通域工作，头发丝之间被围住的底色它抠不掉。
    这里在角色 mask 内部再找一遍「接近纯白」的像素，把它们补挖成缝。
    """
    white = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, white).convert("L")
    near = diff.point(lambda v: 255 if v <= tol else 0)
    holes = ImageChops.multiply(near, mask)
    holes = holes.filter(ImageFilter.MedianFilter(3))
    return holes.filter(ImageFilter.GaussianBlur(0.6))


def content_bbox(mask, margin=0.02):
    box = mask.point(lambda v: 255 if v > 128 else 0).getbbox()
    if not box:
        return None
    pad_x = int((box[2] - box[0]) * margin)
    pad_y = int((box[3] - box[1]) * margin)
    return (
        max(0, box[0] - pad_x),
        max(0, box[1] - pad_y),
        min(mask.width, box[2] + pad_x),
        min(mask.height, box[3] + pad_y),
    )


# ---------------------------------------------------------------- 点阵渲染

def levels(gray, mask):
    """用角色像素的直方图分位数取色阶范围(mask 非零的像素参与统计)。"""
    hist = gray.histogram(mask)
    total = sum(hist)
    if total == 0:
        return 0, 255
    acc, lo, hi = 0, 0, 255
    lo_target, hi_target = total * 0.005, total * 0.995
    for v in range(256):
        acc += hist[v]
        if acc <= lo_target:
            lo = v
        if acc <= hi_target:
            hi = v
    if hi - lo < 8:
        hi = min(255, lo + 8)
    return lo, hi


def build_dots(gray, mask, holes, out_w, out_h, cell, ss):
    """按六边形密排算出每个格点中心，及其采样到的灰度 / mask / 内部背景洞的值。"""
    cell_ss = cell * ss
    row_step = cell_ss * math.sqrt(3) / 2.0
    cols = int(out_w * ss / cell_ss)
    rows = int(math.floor((out_h * ss - 2) / row_step))
    pad_x = (out_w * ss - cols * cell_ss + cell_ss) / 2.0
    pad_y = (out_h * ss - (rows - 1) * row_step) / 2.0

    sx = gray.width / float(out_w * ss)
    sy = gray.height / float(out_h * ss)
    px = gray.load()
    pm = mask.load() if mask is not None else None
    ph = holes.load() if holes is not None else None

    dots = []
    for r in range(rows):
        y = pad_y + r * row_step
        offset = cell_ss / 2.0 if r % 2 else 0.0
        n = cols - 1 if r % 2 else cols
        for c in range(n):
            x = pad_x + offset + c * cell_ss
            gx = min(gray.width - 1, max(0, int(x * sx)))
            gy = min(gray.height - 1, max(0, int(y * sy)))
            m = pm[gx, gy] if pm is not None else 255
            hl = ph[gx, gy] if ph is not None else 0
            dots.append((x, y, px[gx, gy], m, hl))
    return dots, cell_ss


def main():
    a = parse_args()
    raw = Image.open(a.src)
    img = raw.convert("RGB")

    mask = None
    holes = None
    mode = None
    if a.no_extract:
        mode = "none"
    elif a.key:
        mode = "key"
        mask = key_mask(img, hex_to_rgb(a.key), a.key_tol)
        if a.white_hole is not None:
            holes = white_holes(img, a.white_hole, mask)
            mode = "key+white"
    elif has_useful_alpha(raw):
        mode = "alpha"
        mask = alpha_mask(raw.convert("RGBA"))
    else:
        mode = "flood"
        mask, holes = background_split(img, a.tol, a.hole_tol)
        if a.no_punch:
            holes = None

    if not a.no_autocrop:
        box = content_bbox(mask if mask is not None else foreground_mask(img, a.tol))
        if box:
            img = img.crop(box)
            if mask is not None:
                mask = mask.crop(box)
            if holes is not None:
                holes = holes.crop(box)

    gray = img.convert("L")

    scale = (a.width * a.ss) / float(img.width)
    out_w = a.width
    out_h = int(round(img.height * scale / a.ss))

    # 采样前按格点大小做一次模糊，等价于取格点邻域的平均明暗
    cell_src = a.cell * (img.width / float(out_w))
    gray = gray.filter(ImageFilter.GaussianBlur(radius=max(0.5, cell_src * 0.5)))

    if mask is not None:
        lo, hi = levels(gray, mask)
    else:
        lo, hi = levels(gray, gray.point(lambda v: 255 if v < a.white else 0))
        # 没抠图时只能靠亮度把背景挡掉
    span = max(1, hi - lo)

    dots, cell_ss = build_dots(gray, mask, holes, out_w, out_h, a.cell, a.ss)
    r_max = cell_ss * 0.5 * 0.97
    r_min = r_max * a.min_ratio

    W, H = int(out_w * a.ss), int(out_h * a.ss)
    bg_color = (0, 0, 0, 0) if a.transparent else hex_to_rgb(a.bg) + (255,)
    canvas = Image.new("RGBA", (W, H), bg_color)
    draw = ImageDraw.Draw(canvas)
    fg = hex_to_rgb(a.fg) + (255,)

    drawn = 0
    skipped_hole = 0
    for x, y, v, m, hl in dots:
        if mask is not None and m < a.mask_thresh:
            continue  # 外部背景：一个点都不画
        if holes is not None and hl >= a.hole_thresh:
            skipped_hole += 1
            continue  # 角色内部的背景缝(头发间隙等)：留空
        if mask is None and v >= a.white:
            continue
        t = (v - lo) / float(span) if a.tone == "light" else (hi - v) / float(span)
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        t = t ** a.gamma
        if t < a.cutoff:
            continue
        r = r_min + (r_max - r_min) * t
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fg)
        drawn += 1

    if a.ss > 1:
        canvas = canvas.resize((out_w, out_h), Image.LANCZOS)
    if not a.transparent:
        canvas = canvas.convert("RGB")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    canvas.save(a.out)
    print(
        "输出 %s  %dx%d  tone=%s 抠图=%s 色阶 %d~%d  画点 %d 个  缝里留空 %d 个"
        % (a.out, out_w, out_h, a.tone, mode, lo, hi, drawn, skipped_hole)
    )


if __name__ == "__main__":
    main()
