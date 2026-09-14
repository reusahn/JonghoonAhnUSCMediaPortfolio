import json
import os
import re
import shutil
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "instagram_ready"
MANIFEST = ROOT / "tools" / "instagram_manifest.json"
ASSETS = ROOT / "assets" / "images"
W, H = 1080, 1350
BG = (4, 4, 4)
WHITE = (241, 241, 238)
MUTED = (148, 148, 145)
LINE = (48, 48, 48)

BANNED = {
    "favicon.png", "profile.jpg", "profile1.jpeg", "profile2.jpg",
    "maya.png", "unity.png", "unreal2.png", "blender.png", "chatgpt.png", "opencv.png"
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "project"


def normalize_repo_path(detail_path, src):
    src = src.strip().split("?")[0].split("#")[0]
    if src.startswith(("http://", "https://", "//", "data:")):
        return None
    p = os.path.normpath(os.path.join(os.path.dirname(detail_path), src))
    p = p.lstrip("./")
    return p


def extract_page_images(detail_path):
    p = ROOT / detail_path
    if not p.exists():
        return []
    html = p.read_text(encoding="utf-8", errors="ignore")
    vals = re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", html, flags=re.I)
    out = []
    for v in vals:
        rp = normalize_repo_path(detail_path, v)
        if not rp:
            continue
        fp = ROOT / rp
        if fp.suffix.lower() in IMAGE_EXTS and "assets/images" in rp.replace("\\", "/") and fp.exists():
            if fp.name.lower() not in BANNED:
                out.append(rp.replace("\\", "/"))
    return list(dict.fromkeys(out))


def base_prefix(cover):
    stem = Path(cover).stem
    stem = re.sub(r"_\d+(?:\s*\(\d+\))?$", "", stem)
    return stem


def valid_image(path):
    fp = ROOT / path
    try:
        with Image.open(fp) as im:
            w, h = im.size
            return w >= 250 and h >= 200
    except Exception:
        return False


def choose_images(item):
    cover = item["cover"]
    candidates = [cover] + extract_page_images(item["detail"])
    candidates = list(dict.fromkeys(candidates))
    candidates = [c for c in candidates if (ROOT / c).exists() and valid_image(c)]

    if len(candidates) < 3:
        pref = base_prefix(cover).lower()
        siblings = []
        for fp in ASSETS.iterdir():
            if fp.is_file() and fp.suffix.lower() in IMAGE_EXTS and fp.name.lower() not in BANNED:
                if fp.stem.lower().startswith(pref) and valid_image(str(fp.relative_to(ROOT))):
                    siblings.append(str(fp.relative_to(ROOT)).replace("\\", "/"))
        for s in sorted(siblings):
            if s not in candidates:
                candidates.append(s)

    # Keep the cover first. Prefer larger page assets for extras while preserving enough variety.
    cover_first = candidates[:1]
    extras = candidates[1:]
    def score(path):
        try:
            return (ROOT / path).stat().st_size
        except Exception:
            return 0
    extras = sorted(extras, key=score, reverse=True)
    return cover_first + extras[:2]


def open_rgb(path):
    im = Image.open(ROOT / path)
    try:
        im.seek(0)
    except Exception:
        pass
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    elif im.mode == "RGBA":
        base = Image.new("RGB", im.size, (0, 0, 0))
        base.paste(im, mask=im.getchannel("A"))
        im = base
    else:
        im = im.convert("RGB")
    return im


def draw_header(draw, title, category, num, cover=False):
    left = 56
    if cover:
        draw.text((left, 50), f"{num:02d}", font=font(18), fill=MUTED)
        draw.line((left + 42, 62, left + 126, 62), fill=LINE, width=1)
        # title size adapts
        size = 52 if len(title) < 28 else 44
        draw.text((left, 92), title, font=font(size, True), fill=WHITE)
        draw.text((left, 164), category.upper(), font=font(18), fill=MUTED)
    else:
        draw.text((left, 44), title, font=font(24, True), fill=WHITE)
        draw.text((W - 112, 47), f"{num:02d}/03", font=font(17), fill=MUTED)
        draw.line((left, 86, W - left, 86), fill=LINE, width=1)


def contain_on_black(canvas, im, box, allow_upscale=True):
    x, y, bw, bh = box
    src = im.copy()
    scale = min(bw / src.width, bh / src.height)
    if not allow_upscale:
        scale = min(scale, 1.0)
    nw = max(1, int(src.width * scale))
    nh = max(1, int(src.height * scale))
    src = src.resize((nw, nh), Image.Resampling.LANCZOS)
    px = x + (bw - nw) // 2
    py = y + (bh - nh) // 2
    canvas.paste(src, (px, py))
    return (px, py, nw, nh)


def make_cover(item, asset, project_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], project_no, cover=True)
    im = open_rgb(asset)
    # Huge real image, minimal framing.
    contain_on_black(canvas, im, (56, 225, W - 112, 1030))
    draw.text((56, 1290), "SELECTED WORK", font=font(15), fill=MUTED)
    draw.text((W - 105, 1288), "01", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_image_slide(item, asset, project_no, slide_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], slide_no, cover=False)
    im = open_rgb(asset)
    contain_on_black(canvas, im, (52, 112, W - 104, 1125))
    draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
    draw.text((W - 108, 1268), f"{slide_no:02d}", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_collage_slide(item, assets, project_no, slide_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], slide_no, cover=False)
    gap = 18
    x = 52
    y = 112
    bw = W - 104
    bh = 1125
    half = (bh - gap) // 2
    for idx, asset in enumerate(assets[:2]):
        im = open_rgb(asset)
        # Center-crop to a wide panel, still entirely based on source imagery.
        panel = ImageOps.fit(im, (bw, half), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        canvas.paste(panel, (x, y + idx * (half + gap)))
    draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
    draw.text((W - 108, 1268), f"{slide_no:02d}", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_contact_sheet(cover_paths):
    thumbs = []
    tw, th = 270, 338
    for p in cover_paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((tw, th), Image.Resampling.LANCZOS)
        cell = Image.new("RGB", (tw, th), BG)
        cell.paste(im, ((tw-im.width)//2, (th-im.height)//2))
        thumbs.append(cell)
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols*tw, rows*th), BG)
    for i, cell in enumerate(thumbs):
        sheet.paste(cell, ((i%cols)*tw, (i//cols)*th))
    sheet.save(OUT / "00_ALL_PROJECTS_CONTACT_SHEET.jpg", quality=91)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    used = []
    covers = []

    for idx, item in enumerate(items, 1):
        slug = f"{idx:02d}_{slugify(item['title'])}"
        folder = OUT / slug
        folder.mkdir(parents=True)
        chosen = choose_images(item)
        if not chosen:
            print(f"WARN no usable assets: {item['title']}")
            continue

        # Always create three upload-ready slides. If source count is low, build a collage from actual source images.
        cover_path = folder / "01_cover.jpg"
        make_cover(item, chosen[0], idx, cover_path)
        covers.append(cover_path)

        if len(chosen) >= 2:
            make_image_slide(item, chosen[1], idx, 2, folder / "02_image.jpg")
        else:
            make_image_slide(item, chosen[0], idx, 2, folder / "02_image.jpg")

        if len(chosen) >= 3:
            make_image_slide(item, chosen[2], idx, 3, folder / "03_image.jpg")
        elif len(chosen) == 2:
            make_collage_slide(item, chosen, idx, 3, folder / "03_collage.jpg")
        else:
            # crop the actual source differently instead of generating new imagery
            im = open_rgb(chosen[0])
            canvas = Image.new("RGB", (W, H), BG)
            draw = ImageDraw.Draw(canvas)
            draw_header(draw, item["title"], item["category"], 3, cover=False)
            crop = ImageOps.fit(im, (W-104, 1125), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            canvas.paste(crop, (52, 112))
            draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
            draw.text((W - 108, 1268), "03", font=font(17), fill=WHITE)
            canvas.save(folder / "03_detail_crop.jpg", quality=95, subsampling=0)

        used.append({
            "order": idx,
            "title": item["title"],
            "detail": item["detail"],
            "selected_source_assets": chosen,
            "note": "Only repository source images were used. No generated imagery."
        })

    (OUT / "SOURCE_AUDIT.json").write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "Instagram-ready portfolio set\n"
        "1080 x 1350 (4:5)\n"
        "Black background / minimal typography / no portfolio URL\n"
        "All artwork imagery is sourced from this repository. No AI-generated project imagery.\n"
        "Each project folder contains 3 upload-ready slides.\n",
        encoding="utf-8"
    )
    make_contact_sheet(covers)
    print(f"Built {len(used)} projects / {len(used)*3} slides")


if __name__ == "__main__":
    main()
