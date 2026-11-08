#!/usr/bin/env python3
"""把一张带背景的插画做成 PV 管线能吃的角色素材（冒烟用）。

产出：
  cutout.png   去掉背景的 RGBA，裁到角色外接框（保留主要连通块）
  sprite.png   935×1682 的立绘画布：头部落在上半部，供 tuikit.sprite_src 的 face/bust/upper 裁剪使用
  dancer.png   420×540 全身画布：脚线位置放在 FOOT_Y，供 placeholder_h3 的 feet()/trace 使用

用法：
  python prepare_character.py 源图.jpg 输出目录
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BG_TOL = 26          # 与背景色的 Euclidean 距离阈值
MIN_AREA = 1500      # 小于这个面积的连通块丢弃（0.25 缩放下）

SPRITE_CANVAS = (935, 1682)
DANCER_CANVAS = (420, 540)
DANCER_FOOT_Y = 528


def estimate_bg(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w, _ = a.shape
    edge = np.concatenate([
        a[:3].reshape(-1, 3), a[-3:].reshape(-1, 3),
        a[:, :3].reshape(-1, 3), a[:, -3:].reshape(-1, 3)])
    return np.median(edge, axis=0)


def cutout(im: Image.Image) -> Image.Image:
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
    bg = estimate_bg(im)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    fg = dist > BG_TOL

    # 从边框洪泛：与背景色接近且连通到边缘的像素 = 真背景
    h, w = fg.shape
    seen = np.zeros((h, w), bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not fg[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if not fg[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and not fg[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    alpha = np.where(seen, 0, 255).astype(np.uint8)

    # 连通过滤（0.25 缩放上做，够快）
    small = Image.fromarray(alpha).resize((w // 4, h // 4), Image.Resampling.NEAREST)
    m = np.asarray(small) > 127
    sh, sw = m.shape
    lab = np.zeros((sh, sw), np.int32); cur = 0
    keep = np.zeros_like(m)
    for y0 in range(sh):
        for x0 in range(sw):
            if m[y0, x0] and lab[y0, x0] == 0:
                cur += 1
                comp = deque([(y0, x0)]); lab[y0, x0] = cur; pts = []
                while comp:
                    y, x = comp.popleft(); pts.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < sh and 0 <= nx < sw and m[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur; comp.append((ny, nx))
                xs = [p[1] for p in pts]
                if len(pts) >= MIN_AREA and 0.08 * sw < sum(xs) / len(xs) < 0.92 * sw:
                    for y, x in pts:
                        keep[y, x] = True
    keep_big = np.asarray(Image.fromarray((keep * 255).astype(np.uint8))
                          .resize((w, h), Image.Resampling.NEAREST)) > 127
    alpha = np.where(keep_big, alpha, 0).astype(np.uint8)

    out = Image.fromarray(np.dstack([np.asarray(im.convert("RGB")), alpha]), "RGBA")
    # 收边：轻微收缩再羽化，去掉背景色描边
    a = out.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out.putalpha(a)
    bbox = out.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    return out.crop(bbox)


def on_canvas(fig: Image.Image, canvas: tuple[int, int], scale: float, cx: float, bottom: float) -> Image.Image:
    w, h = canvas
    nw, nh = max(1, round(fig.width * scale)), max(1, round(fig.height * scale))
    f = fig.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(f, (round(cx - nw / 2), round(bottom - nh)))
    return out


def main() -> int:
    src = Path(sys.argv[1]); dst = Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    fig = cutout(im)
    print(f"cutout: {fig.size}  (源 {im.size})")
    fig.save(dst / "cutout.png")

    # 立绘画布：按原立绘的取景复刻——头宽约 440 px、头顶贴 y=0，
    # 这样 seg_page.avatars() 的固定裁剪 (250,40,690,480) 和 sprite_src 的 face/bust 裁剪都能对上
    sw, sh = SPRITE_CANVAS
    target_w = 490
    sprite = on_canvas(fig, SPRITE_CANVAS, target_w / fig.width, sw / 2, fig.height * (target_w / fig.width))
    sprite.save(dst / "sprite.png")
    print("sprite:", sprite.size)

    # 舞者画布：底部对齐脚线，高度约 408
    dw, dh = DANCER_CANVAS
    dancer = on_canvas(fig, DANCER_CANVAS, 408 / fig.height, dw / 2, DANCER_FOOT_Y)
    dancer.save(dst / "dancer.png")
    print("dancer:", dancer.size)

    # 预览：三张拼一张，黑底，方便看透明通道
    pv = Image.new("RGB", (sw + dw + 60, max(sh, dh) + 20), (8, 10, 16))
    pv.paste(sprite, (0, 10), sprite)
    pv.paste(dancer, (sw + 30, 10), dancer)
    pv.paste(fig.resize((min(fig.width, 420), round(fig.height * min(fig.width, 420) / fig.width))),
             (sw + 30, 10), fig.resize((min(fig.width, 420), round(fig.height * min(fig.width, 420) / fig.width))))
    pv.save(dst / "preview_assets.png")
    print("preview:", dst / "preview_assets.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
