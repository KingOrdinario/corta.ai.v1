
import os, uuid, threading, traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
from processor import process_video, download_youtube

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "1500")) * 1024 * 1024
app.secret_key = os.getenv("FLASK_SECRET_KEY", "corta-ai-development-key")

jobs = {}

def run_job(job_id, source_type, source, options):
    job = jobs[job_id]
    try:
        job["status"] = "processing"
        job["message"] = "Preparando vídeo..."
        if source_type == "youtube":
            job["message"] = "Baixando vídeo do YouTube..."
            input_path = download_youtube(source, UPLOADS / job_id)
        else:
            input_path = Path(source)

        def progress(pct, msg):
            job["progress"] = max(0, min(100, int(pct)))
            job["message"] = msg

        clips = process_video(
            input_path=input_path,
            output_dir=OUTPUTS / job_id,
            count=int(options.get("count", 5)),
            target_duration=int(options.get("duration", 60)),
            aspect=options.get("aspect", "9:16"),
            subtitles=bool(options.get("subtitles", True)),
            progress=progress,
        )
        job["clips"] = clips
        job["status"] = "done"
        job["progress"] = 100
        job["message"] = "Cortes prontos."
    except Exception as e:
        traceback.print_exc()
        job["status"] = "error"
        job["message"] = str(e) or "Erro inesperado durante o processamento."

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/app.js")
def app_js():
    return send_from_directory(BASE, "app.js")

@app.get("/style.css")
def style_css():
    return send_from_directory(BASE, "style.css")

@app.get("/corta-ai-logo.png")
def logo():
    return send_from_directory(BASE, "corta-ai-logo.png")

@app.post("/api/process")
def process():
    source_type = request.form.get("source_type", "file")
    options = {
        "count": request.form.get("count", "5"),
        "duration": request.form.get("duration", "60"),
        "aspect": request.form.get("aspect", "9:16"),
        "subtitles": request.form.get("subtitles", "1") == "1",
    }
    job_id = uuid.uuid4().hex[:12]
    if source_type == "youtube":
        url = (request.form.get("youtube_url") or "").strip()
        if not url.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
            return jsonify({"error": "Informe um link válido do YouTube."}), 400
        source = url
    else:
        f = request.files.get("video")
        if not f or not f.filename:
            return jsonify({"error": "Selecione um vídeo."}), 400
        filename = secure_filename(f.filename) or "video.mp4"
        path = UPLOADS / f"{job_id}_{filename}"
        f.save(path)
        source = str(path)

    jobs[job_id] = {"status": "queued", "progress": 0, "message": "Na fila...", "clips": []}
    t = threading.Thread(target=run_job, args=(job_id, source_type, source, options), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})

@app.get("/api/job/<job_id>")
def job_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job não encontrado."}), 404
    return jsonify(jobs[job_id])

@app.get("/media/<job_id>/<path:filename>")
def media(job_id, filename):
    directory = OUTPUTS / job_id
    if not directory.exists():
        abort(404)
    return send_from_directory(directory, filename, as_attachment=False)

@app.get("/download/<job_id>/<path:filename>")
def download(job_id, filename):
    directory = OUTPUTS / job_id
    if not directory.exists():
        abort(404)
    return send_from_directory(directory, filename, as_attachment=True)

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Arquivo muito grande para a configuração atual."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
