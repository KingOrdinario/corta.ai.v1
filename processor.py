
import re, subprocess, json, math, shutil
from pathlib import Path

WHISPER_MODEL = None

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stdout[-5000:])
    return p.stdout

def download_youtube(url, workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "%(id)s.%(ext)s"
    run(["yt-dlp", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", str(out), url])
    files = list(workdir.glob("*"))
    videos = [p for p in files if p.suffix.lower() in {".mp4",".mkv",".webm",".mov"}]
    if not videos:
        raise RuntimeError("Não foi possível obter o vídeo do YouTube.")
    return max(videos, key=lambda p: p.stat().st_size)

def duration(path):
    data = run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(path)])
    return float(json.loads(data)["format"]["duration"])

def transcribe(path):
    # Faster-Whisper is loaded only when needed. No external API.
    global WHISPER_MODEL
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return []
    if WHISPER_MODEL is None:
        model_name = __import__("os").environ.get("WHISPER_MODEL", "tiny")
        WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = WHISPER_MODEL.transcribe(str(path), beam_size=1, vad_filter=True, word_timestamps=True)
    result = []
    for s in segments:
        text = (s.text or "").strip()
        if text:
            result.append({"start": float(s.start), "end": float(s.end), "text": text})
    return result

HOOKS = [
    "segredo","ninguém","nunca","sempre","erro","verdade","incrível","surpresa","problema",
    "descobri","importante","atenção","por que","como","resultado","milhões","perdeu","ganhou",
    "funciona","não acredito","primeiro","último","melhor","pior","cuidado","exatamente"
]

def choose_windows(segments, total, count, target):
    if not segments:
        # Safe fallback if audio/transcription isn't available.
        usable = min(target, max(5, total))
        if total <= usable:
            starts = [0] * count
        else:
            starts = [(total-usable) * i / max(1, count-1) for i in range(count)]
        return [(s, min(usable, total-s)) for s in starts]

    # Score transcript windows. Candidate centers come from segments.
    scored = []
    for i, s in enumerate(segments):
        text = s["text"].lower()
        score = sum(2.0 for h in HOOKS if h in text)
        score += min(3.0, len(re.findall(r"[!?]", s["text"])) * 0.8)
        score += min(2.0, max(0, len(s["text"].split()) - 12) / 30)
        if i and segments[i-1]["text"].strip().endswith(("?", "!")):
            score += 0.7
        scored.append((score, i))

    scored.sort(reverse=True)
    picked = []
    for score, i in scored:
        center = (segments[i]["start"] + segments[i]["end"]) / 2
        start = max(0, center - target * 0.45)
        end = min(total, start + target)
        start = max(0, end - target)
        if all(abs(start - p[0]) > target * 0.55 for p in picked):
            picked.append((start, min(target, total-start), score))
        if len(picked) >= count:
            break

    if len(picked) < count:
        for i in range(count-len(picked)):
            maxstart=max(0,total-target)
            s=maxstart*i/max(1,count-1)
            if all(abs(s-p[0])>target*.45 for p in picked):
                picked.append((s,min(target,total-s),0))
    picked.sort(key=lambda x:x[0])
    return [(x[0],x[1]) for x in picked[:count]]

def srt_time(seconds):
    ms=int(round((seconds-int(seconds))*1000))
    total=int(seconds)
    h=total//3600; m=(total%3600)//60; s=total%60
    if ms>=1000: s+=1; ms-=1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt(segments, start, end, path):
    lines=[]; idx=1
    for s in segments:
        a=max(start,s["start"]); b=min(end,s["end"])
        if b<=a: continue
        text=s["text"].strip()
        if not text: continue
        lines += [str(idx), f"{srt_time(a-start)} --> {srt_time(b-start)}", text, ""]
        idx+=1
    Path(path).write_text("\n".join(lines), encoding="utf-8")

def make_clip(input_path, out_path, start, length, aspect, srt=None):
    vf=[]
    if aspect=="9:16":
        vf.append("scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black")
    elif aspect=="1:1":
        vf.append("scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=black")
    else:
        vf.append("scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black")
    if srt and Path(srt).exists():
        # subtitles filter path escaping for ffmpeg filter syntax
        p=str(Path(srt).resolve()).replace("\\","/").replace(":","\\:")
        vf.append(f"subtitles='{p}':force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=70'")
    cmd=["ffmpeg","-y","-ss",f"{start:.3f}","-i",str(input_path),"-t",f"{length:.3f}","-vf",",".join(vf),"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",str(out_path)]
    run(cmd)

def process_video(input_path, output_dir, count, target_duration, aspect, subtitles, progress):
    input_path=Path(input_path); output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    total=duration(input_path)
    progress(8,"Extraindo áudio e analisando o vídeo...")
    segments=transcribe(input_path)
    progress(35,"Encontrando os melhores momentos...")
    windows=choose_windows(segments,total,count,target_duration)
    results=[]
    for i,(start,length) in enumerate(windows,1):
        srt=None
        if subtitles and segments:
            srt=output_dir/f"clip_{i:02d}.srt"
            write_srt(segments,start,start+length,srt)
        progress(40 + int((i-1)/max(1,len(windows))*55), f"Renderizando corte {i} de {len(windows)}...")
        out=output_dir/f"corta-ai-corte-{i:02d}.mp4"
        make_clip(input_path,out,start,length,aspect,srt)
        if srt and srt.exists():
            srt.unlink()
        results.append({"name":out.name,"url":f"/media/{output_dir.name}/{out.name}","download":f"/download/{output_dir.name}/{out.name}","start":round(start,1),"duration":round(length,1),"score":None})
    progress(100,"Cortes prontos.")
    return results
