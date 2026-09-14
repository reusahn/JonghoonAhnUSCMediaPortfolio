import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / ".instagram_video_frames"
DIAGRAM_DIR = ROOT / ".instagram_diagrams"
VIDEO_DIR.mkdir(exist_ok=True)
DIAGRAM_DIR.mkdir(exist_ok=True)

VIDEO_PROJECTS = {
    "when-it-seen": ["https://vimeo.com/1219183858"],
    "the-way-to-be-oneself": [
        "https://vimeo.com/1143335967/25404ae421",
        "https://player.vimeo.com/video/1143335967?h=25404ae421",
    ],
    "jooan": ["https://vimeo.com/1219693160", "https://vimeo.com/1218744311"],
}

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def download_video(url, dest):
    if dest.exists() and dest.stat().st_size > 100000:
        return True
    cmd = [
        sys.executable, "-m", "yt_dlp", "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4", "-o", str(dest), url,
    ]
    p = run(cmd)
    print(p.stdout[-2000:])
    return dest.exists() and dest.stat().st_size > 100000


def duration(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    try:
        return float(p.stdout.strip())
    except Exception:
        return 12.0


def extract_frame(video, t, dest):
    p = run(["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(dest)])
    if not dest.exists():
        print("ffmpeg failed", p.stdout[-1500:])
    return dest.exists()


def prepare_video_frames():
    for slug, urls in VIDEO_PROJECTS.items():
        videos = []
        for i, url in enumerate(urls, 1):
            v = VIDEO_DIR / f"_{slug}_source_{i}.mp4"
            if download_video(url, v):
                videos.append(v)
                # For The Way To Be Oneself, the second URL is just a fallback for the same video.
                if slug == "the-way-to-be-oneself":
                    break
        if not videos:
            print("WARN: no downloadable Vimeo video for", slug)
            continue

        frame_specs = []
        if len(videos) == 1:
            d = duration(videos[0])
            frame_specs = [(videos[0], d * 0.18), (videos[0], d * 0.50), (videos[0], d * 0.82)]
        else:
            d1 = duration(videos[0])
            d2 = duration(videos[1])
            frame_specs = [(videos[0], d1 * 0.24), (videos[0], d1 * 0.68), (videos[1], d2 * 0.52)]

        for n, (video, t) in enumerate(frame_specs, 1):
            dest = VIDEO_DIR / f"{slug}_{n:02d}.jpg"
            extract_frame(video, max(t, 0.1), dest)


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def centered_text(draw, text, y, fnt, fill, w=1600):
    box = draw.textbbox((0, 0), text, font=fnt)
    tw = box[2] - box[0]
    draw.text(((w - tw)//2, y), text, font=fnt, fill=fill)


def technical_diagram(path, title, kicker, nodes, footer):
    W, H = 1600, 1000
    bg = (8, 10, 12)
    fg = (240, 240, 236)
    muted = (150, 154, 158)
    line = (55, 62, 68)
    accent = (120, 150, 178)
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.text((90, 70), kicker.upper(), font=font(22), fill=muted)
    d.text((90, 118), title, font=font(50, True), fill=fg)
    d.line((90, 200, 1510, 200), fill=line, width=2)

    top = 315
    n = len(nodes)
    left, right = 100, 1500
    gap = 18
    bw = int((right-left-gap*(n-1))/n)
    for i, (head, sub) in enumerate(nodes):
        x = left + i*(bw+gap)
        d.rounded_rectangle((x, top, x+bw, top+270), radius=20, outline=line, width=2, fill=(14,17,20))
        d.text((x+24, top+30), f"{i+1:02d}", font=font(18, True), fill=accent)
        d.text((x+24, top+82), head, font=font(26, True), fill=fg)
        # manual small wrapping
        words = sub.split()
        lines, cur = [], ""
        for word in words:
            test = (cur + " " + word).strip()
            if d.textlength(test, font=font(18)) > bw-48 and cur:
                lines.append(cur); cur = word
            else:
                cur = test
        if cur: lines.append(cur)
        yy = top+135
        for line_txt in lines[:4]:
            d.text((x+24, yy), line_txt, font=font(18), fill=muted)
            yy += 29
        if i < n-1:
            ax = x+bw+4
            d.line((ax, top+135, ax+gap-8, top+135), fill=accent, width=2)
            d.polygon([(ax+gap-8, top+130),(ax+gap-8, top+140),(ax+gap-1, top+135)], fill=accent)

    d.line((90, 720, 1510, 720), fill=line, width=2)
    d.text((90, 770), footer, font=font(25), fill=fg)
    d.text((90, 830), "Portfolio evidence is intentionally diagram-based because no verified RenderDoc screenshot is presented as evidence.", font=font(17), fill=muted)
    im.save(path, quality=95)


def prepare_android_diagrams():
    technical_diagram(
        DIAGRAM_DIR / "android-renderdoc_01.png",
        "Android Delivery & RenderDoc Workflow",
        "Runtime Profiling · Deployment",
        [
            ("Unity Project", "Real-time application prepared for Android delivery"),
            ("APK Build", "Build and package the Unity application"),
            ("Mobile Validation", "Run and validate on Android hardware"),
        ],
        "Build → deploy → validate on target hardware."
    )
    technical_diagram(
        DIAGRAM_DIR / "android-renderdoc_02.png",
        "Graphics Debugging",
        "RenderDoc · Unity",
        [
            ("Frame Issue", "Identify rendering or graphics behavior that needs investigation"),
            ("Frame Capture", "Capture a Unity frame with RenderDoc"),
            ("Inspect", "Review rendering behavior and isolate the likely cause"),
        ],
        "Observe the frame before changing the system."
    )
    technical_diagram(
        DIAGRAM_DIR / "android-renderdoc_03.png",
        "Validation Loop",
        "Production Debugging",
        [
            ("Isolate", "Separate asset material shader and runtime causes"),
            ("Repair", "Apply the lowest-risk change that preserves the visual target"),
            ("Re-test", "Validate again in the engine and target presentation context"),
        ],
        "Profile → isolate → repair → validate."
    )


if __name__ == "__main__":
    prepare_video_frames()
    prepare_android_diagrams()
