import json
import os
import re
import shutil
import unicodedata
import urllib.request
from urllib.parse import urljoin, urlparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "instagram_ready"
MANIFEST = ROOT / "tools" / "instagram_manifest.json"
ASSETS = ROOT / "assets" / "images"
CACHE = ROOT / ".instagram_source_cache"
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
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower() or "project"


def normalize_repo_path(detail_path, src):
    src = src.strip().split("?")[0].split("#")[0]
    if src.startswith(("http://", "https://", "//", "data:")):
        return None
    p = os.path.normpath(os.path.join(os.path.dirname(detail_path), src)).lstrip("./")
    return p


def extract_page_images(detail_path):
    if not detail_path:
        return []
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
        if fp.suffix.lower() in IMAGE_EXTS and "assets/images" in rp.replace("\\", "/") and fp.exists() and fp.name.lower() not in BANNED:
            out.append(rp.replace("\\", "/"))
    return list(dict.fromkeys(out))


def download_remote(url):
    CACHE.mkdir(exist_ok=True)
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in IMAGE_EXTS:
        suffix = ".jpg"
    key = slugify(parsed.netloc + parsed.path)[:90] + suffix
    dest = CACHE / key
    if dest.exists() and dest.stat().st_size > 1000:
        return str(dest.relative_to(ROOT))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r, open(dest, "wb") as f:
            f.write(r.read())
        with Image.open(dest) as im:
            im.verify()
        return str(dest.relative_to(ROOT))
    except Exception as e:
        print("WARN remote download failed", url, e)
        if dest.exists():
            dest.unlink()
        return None


def extract_remote_page_images(page_url):
    if not page_url:
        return []
    try:
        req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("WARN remote page failed", page_url, e)
        return []
    vals = re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", html, flags=re.I)
    out = []
    for v in vals:
        clean = v.split("?")[0].split("#")[0]
        if Path(clean).suffix.lower() not in IMAGE_EXTS:
            continue
        u = urljoin(page_url, v)
        if "jonghoonahn.com" not in u:
            continue
        dl = download_remote(u)
        if dl:
            out.append(dl)
    return list(dict.fromkeys(out))


def base_prefix(cover):
    stem = Path(cover).stem
    return re.sub(r"_\d+(?:\s*\(\d+\))?$", "", stem)


def valid_image(path):
    try:
        with Image.open(ROOT / path) as im:
            w, h = im.size
            return w >= 250 and h >= 200
    except Exception:
        return False


def choose_images(item):
    candidates = []
    cover = item.get("cover")
    if cover:
        candidates.append(cover)
    candidates += item.get("local_assets", [])
    candidates += extract_page_images(item.get("detail"))
    candidates += extract_remote_page_images(item.get("remote_page"))
    for url in item.get("remote_assets", []):
        dl = download_remote(url)
        if dl:
            candidates.append(dl)

    candidates = list(dict.fromkeys(candidates))
    candidates = [c for c in candidates if (ROOT / c).exists() and valid_image(c)]

    if cover and len(candidates) < 3 and (ROOT / cover).exists():
        pref = base_prefix(cover).lower()
        for fp in sorted(ASSETS.iterdir()):
            rel = str(fp.relative_to(ROOT)).replace("\\", "/")
            if fp.is_file() and fp.suffix.lower() in IMAGE_EXTS and fp.name.lower() not in BANNED and fp.stem.lower().startswith(pref) and valid_image(rel):
                if rel not in candidates:
                    candidates.append(rel)

    if not candidates:
        return []
    first = candidates[0]
    extras = candidates[1:]
    def score(path):
        try:
            return (ROOT / path).stat().st_size
        except Exception:
            return 0
    extras = sorted(extras, key=score, reverse=True)
    return [first] + extras[:2]


def open_rgb(path):
    im = Image.open(ROOT / path)
    try:
        im.seek(0)
    except Exception:
        pass
    if im.mode == "RGBA":
        base = Image.new("RGB", im.size, (0, 0, 0))
        base.paste(im, mask=im.getchannel("A"))
        return base
    return im.convert("RGB")


def draw_header(draw, title, category, num, cover=False):
    left = 56
    if cover:
        draw.text((left, 50), f"{num:02d}", font=font(18), fill=MUTED)
        draw.line((left + 42, 62, left + 126, 62), fill=LINE, width=1)
        size = 52 if len(title) < 28 else 44
        draw.text((left, 92), title, font=font(size, True), fill=WHITE)
        draw.text((left, 164), category.upper(), font=font(18), fill=MUTED)
    else:
        draw.text((left, 44), title, font=font(24, True), fill=WHITE)
        draw.text((W - 112, 47), f"{num:02d}/03", font=font(17), fill=MUTED)
        draw.line((left, 86, W - left, 86), fill=LINE, width=1)


def contain_on_black(canvas, im, box):
    x, y, bw, bh = box
    scale = min(bw / im.width, bh / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    src = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(src, (x + (bw - nw)//2, y + (bh - nh)//2))


def make_cover(item, asset, project_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], project_no, True)
    contain_on_black(canvas, open_rgb(asset), (56, 225, W - 112, 1030))
    draw.text((56, 1290), "SELECTED WORK", font=font(15), fill=MUTED)
    draw.text((W - 105, 1288), "01", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_image_slide(item, asset, slide_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], slide_no, False)
    contain_on_black(canvas, open_rgb(asset), (52, 112, W - 104, 1125))
    draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
    draw.text((W - 108, 1268), f"{slide_no:02d}", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_collage_slide(item, assets, slide_no, dest):
    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, item["title"], item["category"], slide_no, False)
    gap, x, y, bw, bh = 18, 52, 112, W - 104, 1125
    half = (bh - gap) // 2
    for idx, asset in enumerate(assets[:2]):
        panel = ImageOps.fit(open_rgb(asset), (bw, half), method=Image.Resampling.LANCZOS)
        canvas.paste(panel, (x, y + idx * (half + gap)))
    draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
    draw.text((W - 108, 1268), f"{slide_no:02d}", font=font(17), fill=WHITE)
    canvas.save(dest, quality=95, subsampling=0)


def make_contact_sheet(paths):
    tw, th, cols = 270, 338, 4
    cells = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((tw, th), Image.Resampling.LANCZOS)
        cell = Image.new("RGB", (tw, th), BG)
        cell.paste(im, ((tw-im.width)//2, (th-im.height)//2))
        cells.append(cell)
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cols*tw, rows*th), BG)
    for i, cell in enumerate(cells):
        sheet.paste(cell, ((i%cols)*tw, (i//cols)*th))
    sheet.save(OUT / "00_ALL_PROJECTS_CONTACT_SHEET.jpg", quality=91)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    if CACHE.exists():
        shutil.rmtree(CACHE)
    OUT.mkdir(parents=True)
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    used, covers = [], []

    for idx, item in enumerate(items, 1):
        folder = OUT / f"{idx:02d}_{slugify(item['title'])}"
        folder.mkdir(parents=True)
        chosen = choose_images(item)
        if not chosen:
            print("WARN no usable assets:", item["title"])
            continue

        cover_path = folder / "01_cover.jpg"
        make_cover(item, chosen[0], idx, cover_path)
        covers.append(cover_path)
        make_image_slide(item, chosen[1] if len(chosen) >= 2 else chosen[0], 2, folder / "02_image.jpg")
        if len(chosen) >= 3:
            make_image_slide(item, chosen[2], 3, folder / "03_image.jpg")
        elif len(chosen) == 2:
            make_collage_slide(item, chosen, 3, folder / "03_collage.jpg")
        else:
            im = open_rgb(chosen[0])
            canvas = Image.new("RGB", (W, H), BG)
            draw = ImageDraw.Draw(canvas)
            draw_header(draw, item["title"], item["category"], 3, False)
            crop = ImageOps.fit(im, (W-104, 1125), method=Image.Resampling.LANCZOS)
            canvas.paste(crop, (52, 112))
            draw.text((56, 1270), item["category"].upper(), font=font(15), fill=MUTED)
            draw.text((W - 108, 1268), "03", font=font(17), fill=WHITE)
            canvas.save(folder / "03_detail_crop.jpg", quality=95, subsampling=0)

        used.append({
            "order": idx,
            "title": item["title"],
            "selected_source_assets": chosen,
            "source_type": "portfolio repository / employment portfolio public media",
            "note": "No AI-generated artwork imagery was used."
        })

    (OUT / "SOURCE_AUDIT.json").write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "Instagram-ready portfolio set\n1080 x 1350 (4:5)\nBlack background / minimal typography / no portfolio URL\nArtwork imagery comes only from Jonghoon Ahn's public portfolio repository or employment-portfolio public media. No AI-generated project imagery.\nEach project folder contains 3 upload-ready slides.\n",
        encoding="utf-8"
    )
    make_contact_sheet(covers)
    print(f"Built {len(used)} projects / {len(used)*3} slides")


if __name__ == "__main__":
    main()
