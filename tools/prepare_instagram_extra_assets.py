from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM_DIR = ROOT / ".instagram_diagrams"
DIAGRAM_DIR.mkdir(exist_ok=True)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size,bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,size)


def diagram(path,title,kicker,nodes,footer,note=""):
    W,H=1600,1000
    bg,fg=(7,7,8),(240,240,236)
    muted,line,accent=(148,148,145),(50,50,52),(170,170,166)
    im=Image.new("RGB",(W,H),bg)
    d=ImageDraw.Draw(im)
    d.text((90,68),kicker.upper(),font=font(21),fill=muted)
    d.text((90,114),title,font=font(48,True),fill=fg)
    d.line((90,198,1510,198),fill=line,width=2)

    top,left,right,gap=315,90,1510,14
    bw=int((right-left-gap*(len(nodes)-1))/len(nodes))
    for i,(head,sub) in enumerate(nodes):
        x=left+i*(bw+gap)
        d.rounded_rectangle((x,top,x+bw,top+270),radius=16,outline=line,width=2,fill=(13,13,14))
        d.text((x+22,top+27),f"{i+1:02d}",font=font(17,True),fill=accent)
        d.text((x+22,top+79),head,font=font(24,True),fill=fg)
        words,lines,cur=sub.split(),[],""
        for word in words:
            test=(cur+" "+word).strip()
            if d.textlength(test,font=font(17))>bw-44 and cur:
                lines.append(cur); cur=word
            else:
                cur=test
        if cur: lines.append(cur)
        yy=top+133
        for txt in lines[:4]:
            d.text((x+22,yy),txt,font=font(17),fill=muted); yy+=28
        if i<len(nodes)-1:
            ax=x+bw+2
            d.line((ax,top+135,ax+gap-6,top+135),fill=accent,width=2)
            d.polygon([(ax+gap-6,top+130),(ax+gap-6,top+140),(ax+gap,top+135)],fill=accent)

    d.line((90,720,1510,720),fill=line,width=2)
    d.text((90,768),footer,font=font(24),fill=fg)
    if note:
        d.text((90,828),note,font=font(16),fill=muted)
    im.save(path,quality=95)


def prepare_the_way_diagrams():
    diagram(
        DIAGRAM_DIR/"the-way-to-be-oneself_01.png",
        "The Way To Be Oneself",
        "Experimental AI Film · 2025",
        [
            ("Intent","Start from the story and emotional question"),
            ("Generate","Explore imagery through ComfyUI workflows"),
            ("Evaluate","Compare outputs and reject weak directions"),
            ("Author","Refine sequence pacing and image relationships"),
            ("Film","Shape generated material into an authored work"),
        ],
        "AI expands the image search space. Filmmaking judgment determines what remains.",
        "Source: the public CG Experimental employment portfolio workflow description."
    )
    diagram(
        DIAGRAM_DIR/"the-way-to-be-oneself_02.png",
        "Visual Development Loop",
        "ComfyUI · Diffusion · Direction",
        [
            ("Question","Define what the scene or image needs to do"),
            ("Branch","Generate multiple visual possibilities"),
            ("Compare","Judge continuity tone and visual consistency"),
            ("Reject","Remove images that do not serve the work"),
            ("Refine","Develop selected material toward the sequence"),
        ],
        "Generation is iterative visual development, not the final authorship step.",
        "No synthetic project still was added here because the public portfolio exposes the film as an embedded video rather than separate still files."
    )
    diagram(
        DIAGRAM_DIR/"the-way-to-be-oneself_03.png",
        "From Image To Sequence",
        "Authored Cinematic Process",
        [
            ("Continuity","Preserve coherence across generated material"),
            ("Tone","Select images that sustain the intended emotional register"),
            ("Pacing","Evaluate duration rhythm and transitions"),
            ("Sequence","Build relationships between images and shots"),
            ("Final Work","Keep only material that serves the film"),
        ],
        "The central problem is turning generated images into cinema.",
        "Source-grounded process slide. No fabricated film frame."
    )


def prepare_android_diagrams():
    diagram(
        DIAGRAM_DIR/"android-renderdoc_01.png",
        "Android Delivery & RenderDoc Workflow",
        "Runtime Profiling · Deployment",
        [
            ("Unity Project","Prepare the real-time application for Android delivery"),
            ("APK Build","Build and package the application"),
            ("Device Test","Validate behavior on Android hardware"),
        ],
        "Build → deploy → validate on target hardware.",
        "Diagram-based evidence is used because the employment portfolio does not claim a verified RenderDoc screenshot."
    )
    diagram(
        DIAGRAM_DIR/"android-renderdoc_02.png",
        "Graphics Debugging",
        "RenderDoc · Unity",
        [
            ("Frame Issue","Identify rendering behavior that needs investigation"),
            ("Frame Capture","Capture a Unity frame with RenderDoc"),
            ("Inspect","Review rendering behavior and isolate likely causes"),
        ],
        "Observe the frame before changing the system.",
        "No fabricated debugger screenshot is presented."
    )
    diagram(
        DIAGRAM_DIR/"android-renderdoc_03.png",
        "Validation Loop",
        "Production Debugging",
        [
            ("Isolate","Separate asset material shader and runtime causes"),
            ("Repair","Apply the lowest-risk production change"),
            ("Re-test","Validate again in engine and target presentation context"),
        ],
        "Profile → isolate → repair → validate.",
        "Source-grounded technical workflow."
    )


if __name__=="__main__":
    prepare_the_way_diagrams()
    prepare_android_diagrams()
