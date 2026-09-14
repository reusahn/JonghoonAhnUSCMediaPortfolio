import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / ".instagram_video_frames"
DIAGRAM_DIR = ROOT / ".instagram_diagrams"
VIDEO_DIR.mkdir(exist_ok=True)
DIAGRAM_DIR.mkdir(exist_ok=True)

# These are the same Vimeo videos embedded in the public employment portfolio pages.
VIMEO_PROJECTS = {
    "when-it-seen": [("1219183858", None)],
    "the-way-to-be-oneself": [("1143335967", "25404ae421")],
    "jooan": [("1219693160", None), ("1218744311", None)],
}

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36",
    "Referer": "https://jonghoonahn.com/",
}


def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download_url(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return dest.exists() and dest.stat().st_size > 100000


def download_vimeo_config_video(video_id, hash_value, dest):
    config_url = f"https://player.vimeo.com/video/{video_id}/config"
    if hash_value:
        config_url += f"?h={hash_value}"
    try:
        cfg = fetch_json(config_url)
    except Exception as e:
        print("VIMEO CONFIG ERROR", video_id, repr(e))
        return False

    files = cfg.get("request", {}).get("files", {})
    progressive = files.get("progressive") or []
    if progressive:
        choices = sorted(progressive, key=lambda x: (x.get("width", 0), x.get("height", 0), x.get("bitrate", 0)), reverse=True)
        for choice in choices:
            url = choice.get("url")
            if not url:
                continue
            try:
                if download_url(url, dest):
                    print("Downloaded progressive Vimeo", video_id, choice.get("width"), choice.get("height"))
                    return True
            except Exception as e:
                print("progressive failed", video_id, repr(e))

    hls = files.get("hls") or {}
    cdns = hls.get("cdns") or {}
    for _, value in cdns.items():
        hls_url = value.get("url") if isinstance(value, dict) else None
        if not hls_url:
            continue
        p = run(["ffmpeg", "-y", "-headers", "Referer: https://jonghoonahn.com/\r\nUser-Agent: Mozilla/5.0\r\n", "-i", hls_url, "-c", "copy", str(dest)])
        if dest.exists() and dest.stat().st_size > 100000:
            print("Downloaded HLS Vimeo", video_id)
            return True
        print("HLS failed", video_id, p.stdout[-1200:])

    thumbs = cfg.get("video", {}).get("thumbs") or {}
    print("No playable stream for", video_id, "available thumbs", list(thumbs.keys()))
    return False


def download_video_fallback(video_id, hash_value, dest):
    urls = []
    if hash_value:
        urls.append(f"https://player.vimeo.com/video/{video_id}?h={hash_value}")
        urls.append(f"https://vimeo.com/{video_id}/{hash_value}")
    else:
        urls.append(f"https://player.vimeo.com/video/{video_id}")
        urls.append(f"https://vimeo.com/{video_id}")
    for url in urls:
        p = run([
            sys.executable, "-m", "yt_dlp", "--no-playlist",
            "-f", "best/bestvideo+bestaudio", "--merge-output-format", "mp4",
            "-o", str(dest), url,
        ])
        print(p.stdout[-1200:])
        if dest.exists() and dest.stat().st_size > 100000:
            return True
    return False


def duration(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    try:
        return float(p.stdout.strip())
    except Exception:
        return 12.0


def extract_frame(video, t, dest):
    p = run(["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(dest)])
    if not dest.exists():
        print("ffmpeg frame failed", p.stdout[-1200:])
    return dest.exists()


def prepare_video_frames():
    for slug, video_specs in VIMEO_PROJECTS.items():
        videos = []
        for i, (video_id, hash_value) in enumerate(video_specs, 1):
            v = VIDEO_DIR / f"_{slug}_source_{i}.mp4"
            ok = download_vimeo_config_video(video_id, hash_value, v)
            if not ok:
                ok = download_video_fallback(video_id, hash_value, v)
            if ok:
                videos.append(v)

        if not videos:
            print("WARN: no embedded Vimeo stream for", slug)
            continue

        if len(videos) == 1:
            d = duration(videos[0])
            specs = [(videos[0], d*0.18), (videos[0], d*0.50), (videos[0], d*0.82)]
        else:
            d1, d2 = duration(videos[0]), duration(videos[1])
            specs = [(videos[0], d1*0.24), (videos[0], d1*0.68), (videos[1], d2*0.52)]
        for n, (video, t) in enumerate(specs, 1):
            extract_frame(video, max(t, 0.1), VIDEO_DIR / f"{slug}_{n:02d}.jpg")


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def technical_diagram(path, title, kicker, nodes, footer):
    W, H = 1600, 1000
    bg, fg = (8,10,12), (240,240,236)
    muted, line, accent = (150,154,158), (55,62,68), (120,150,178)
    im = Image.new("RGB", (W,H), bg)
    d = ImageDraw.Draw(im)
    d.text((90,70), kicker.upper(), font=font(22), fill=muted)
    d.text((90,118), title, font=font(50,True), fill=fg)
    d.line((90,200,1510,200), fill=line, width=2)
    top, left, right, gap = 315, 100, 1500, 18
    bw = int((right-left-gap*(len(nodes)-1))/len(nodes))
    for i,(head,sub) in enumerate(nodes):
        x = left+i*(bw+gap)
        d.rounded_rectangle((x,top,x+bw,top+270), radius=20, outline=line, width=2, fill=(14,17,20))
        d.text((x+24,top+30), f"{i+1:02d}", font=font(18,True), fill=accent)
        d.text((x+24,top+82), head, font=font(26,True), fill=fg)
        words, lines, cur = sub.split(), [], ""
        for word in words:
            test = (cur+" "+word).strip()
            if d.textlength(test,font=font(18)) > bw-48 and cur:
                lines.append(cur); cur=word
            else:
                cur=test
        if cur: lines.append(cur)
        yy=top+135
        for txt in lines[:4]:
            d.text((x+24,yy),txt,font=font(18),fill=muted); yy+=29
        if i < len(nodes)-1:
            ax=x+bw+4
            d.line((ax,top+135,ax+gap-8,top+135),fill=accent,width=2)
            d.polygon([(ax+gap-8,top+130),(ax+gap-8,top+140),(ax+gap-1,top+135)],fill=accent)
    d.line((90,720,1510,720),fill=line,width=2)
    d.text((90,770),footer,font=font(25),fill=fg)
    d.text((90,830),"Diagram-based evidence: the portfolio does not present a verified RenderDoc screenshot.",font=font(17),fill=muted)
    im.save(path,quality=95)


def prepare_android_diagrams():
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_01.png","Android Delivery & RenderDoc Workflow","Runtime Profiling · Deployment",[("Unity Project","Real-time application prepared for Android delivery"),("APK Build","Build and package the Unity application"),("Mobile Validation","Run and validate on Android hardware")],"Build → deploy → validate on target hardware.")
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_02.png","Graphics Debugging","RenderDoc · Unity",[("Frame Issue","Identify rendering or graphics behavior that needs investigation"),("Frame Capture","Capture a Unity frame with RenderDoc"),("Inspect","Review rendering behavior and isolate the likely cause")],"Observe the frame before changing the system.")
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_03.png","Validation Loop","Production Debugging",[("Isolate","Separate asset material shader and runtime causes"),("Repair","Apply the lowest-risk change that preserves the visual target"),("Re-test","Validate again in engine and target presentation context")],"Profile → isolate → repair → validate.")


if __name__ == "__main__":
    prepare_video_frames()
    prepare_android_diagrams()
