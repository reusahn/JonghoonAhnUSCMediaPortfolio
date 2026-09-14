import json
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / ".instagram_video_frames"
DIAGRAM_DIR = ROOT / ".instagram_diagrams"
VIDEO_DIR.mkdir(exist_ok=True)
DIAGRAM_DIR.mkdir(exist_ok=True)

# Same videos embedded in the public employment portfolio pages.
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
FFMPEG_HEADERS = "Referer: https://jonghoonahn.com/\r\nUser-Agent: Mozilla/5.0\r\n"


def run(cmd, timeout=90):
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        class R: pass
        r=R(); r.stdout=(e.stdout or "") + "\nTIMEOUT"; r.returncode=124
        return r


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def vimeo_stream(video_id, hash_value=None):
    url = f"https://player.vimeo.com/video/{video_id}/config"
    if hash_value:
        url += f"?h={hash_value}"
    cfg = fetch_json(url)
    duration = float(cfg.get("video", {}).get("duration") or 12.0)
    files = cfg.get("request", {}).get("files", {})
    progressive = files.get("progressive") or []
    if progressive:
        # 720p/1080p is sufficient for an Instagram 1080px layout and seeks quickly.
        choices = sorted(progressive, key=lambda x: (x.get("width",0), x.get("bitrate",0)))
        suitable = [x for x in choices if 640 <= x.get("width",0) <= 1920]
        chosen = suitable[-1] if suitable else choices[-1]
        return chosen.get("url"), duration, "progressive"
    hls = files.get("hls") or {}
    for value in (hls.get("cdns") or {}).values():
        if isinstance(value, dict) and value.get("url"):
            return value["url"], duration, "hls"
    return None, duration, None


def capture_stream_frame(stream_url, t, dest):
    # Seek directly in the embeddable Vimeo stream. The whole video is never downloaded.
    cmds = [
        ["ffmpeg", "-y", "-headers", FFMPEG_HEADERS, "-ss", f"{t:.3f}", "-i", stream_url, "-frames:v", "1", "-q:v", "2", str(dest)],
        ["ffmpeg", "-y", "-headers", FFMPEG_HEADERS, "-i", stream_url, "-ss", f"{t:.3f}", "-frames:v", "1", "-q:v", "2", str(dest)],
    ]
    for cmd in cmds:
        p = run(cmd, timeout=75)
        if dest.exists() and dest.stat().st_size > 10000:
            return True
        print("frame capture attempt failed", p.stdout[-1000:])
    return False


def prepare_video_frames():
    for slug, specs in VIMEO_PROJECTS.items():
        sources=[]
        for video_id, hash_value in specs:
            try:
                stream, dur, kind = vimeo_stream(video_id, hash_value)
                if stream:
                    print("Vimeo stream ready", slug, video_id, kind, dur)
                    sources.append((stream,dur))
            except Exception as e:
                print("Vimeo config failed", slug, video_id, repr(e))
        if not sources:
            print("WARN no Vimeo stream", slug)
            continue
        if len(sources)==1:
            stream,d=sources[0]
            frame_specs=[(stream,d*.18),(stream,d*.50),(stream,d*.82)]
        else:
            s1,d1=sources[0]; s2,d2=sources[1]
            frame_specs=[(s1,d1*.24),(s1,d1*.68),(s2,d2*.52)]
        ok=0
        for n,(stream,t) in enumerate(frame_specs,1):
            dest=VIDEO_DIR/f"{slug}_{n:02d}.jpg"
            if capture_stream_frame(stream,max(t,.1),dest):
                ok+=1
        print("Captured frames", slug, ok, "/ 3")


def font(size,bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,size)


def technical_diagram(path,title,kicker,nodes,footer):
    W,H=1600,1000
    bg,fg=(8,10,12),(240,240,236)
    muted,line,accent=(150,154,158),(55,62,68),(120,150,178)
    im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im)
    d.text((90,70),kicker.upper(),font=font(22),fill=muted)
    d.text((90,118),title,font=font(50,True),fill=fg)
    d.line((90,200,1510,200),fill=line,width=2)
    top,left,right,gap=315,100,1500,18
    bw=int((right-left-gap*(len(nodes)-1))/len(nodes))
    for i,(head,sub) in enumerate(nodes):
        x=left+i*(bw+gap)
        d.rounded_rectangle((x,top,x+bw,top+270),radius=20,outline=line,width=2,fill=(14,17,20))
        d.text((x+24,top+30),f"{i+1:02d}",font=font(18,True),fill=accent)
        d.text((x+24,top+82),head,font=font(26,True),fill=fg)
        words,lines,cur=sub.split(),[],""
        for word in words:
            test=(cur+" "+word).strip()
            if d.textlength(test,font=font(18))>bw-48 and cur:
                lines.append(cur); cur=word
            else: cur=test
        if cur: lines.append(cur)
        yy=top+135
        for txt in lines[:4]:
            d.text((x+24,yy),txt,font=font(18),fill=muted); yy+=29
        if i<len(nodes)-1:
            ax=x+bw+4; d.line((ax,top+135,ax+gap-8,top+135),fill=accent,width=2)
            d.polygon([(ax+gap-8,top+130),(ax+gap-8,top+140),(ax+gap-1,top+135)],fill=accent)
    d.line((90,720,1510,720),fill=line,width=2)
    d.text((90,770),footer,font=font(25),fill=fg)
    d.text((90,830),"Diagram-based evidence: the portfolio does not present a verified RenderDoc screenshot.",font=font(17),fill=muted)
    im.save(path,quality=95)


def prepare_android_diagrams():
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_01.png","Android Delivery & RenderDoc Workflow","Runtime Profiling · Deployment",[("Unity Project","Real-time application prepared for Android delivery"),("APK Build","Build and package the Unity application"),("Mobile Validation","Run and validate on Android hardware")],"Build → deploy → validate on target hardware.")
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_02.png","Graphics Debugging","RenderDoc · Unity",[("Frame Issue","Identify rendering or graphics behavior that needs investigation"),("Frame Capture","Capture a Unity frame with RenderDoc"),("Inspect","Review rendering behavior and isolate the likely cause")],"Observe the frame before changing the system.")
    technical_diagram(DIAGRAM_DIR/"android-renderdoc_03.png","Validation Loop","Production Debugging",[("Isolate","Separate asset material shader and runtime causes"),("Repair","Apply the lowest-risk change that preserves the visual target"),("Re-test","Validate again in engine and target presentation context")],"Profile → isolate → repair → validate.")

if __name__=="__main__":
    prepare_video_frames()
    prepare_android_diagrams()
