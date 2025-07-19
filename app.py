from flask import Flask, request, jsonify, send_file, send_from_directory
import subprocess
import os
import time
import json
import re
import platform

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── DYNAMIC YTDLP PATH ──────────────────────────────────────────
if platform.system() == "Windows":
    YTDLP_PATH = r"D:\downloader\yt-dlp.exe"
else:
    # On Linux (Render) we'll have yt-dlp installed via requirements.txt
    YTDLP_PATH = "yt-dlp"

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    format_type = data.get("format")

    if not url or format_type not in ["audio", "video"]:
        return jsonify({"error": "Invalid input"}), 400
    
    # If it's a YouTube link, rewrite via Invidious to bypass bot checks
    if "youtube.com/watch" in url or "youtu.be/" in url:
        m = re.search(r"(?:v=|youtu\.be/)([^&?/]+)", url)
        if m:
            video_id = m.group(1)
            url = f"https://yewtu.be/watch?v={video_id}"

    # Clean downloads folder
    for f in os.listdir(DOWNLOAD_DIR):
        os.remove(os.path.join(DOWNLOAD_DIR, f))

    # Fetch metadata -> title
    try:
        res = subprocess.run(
            [YTDLP_PATH, "--dump-json", url],
            capture_output=True, text=True, check=True
        )
        info = json.loads(res.stdout)
        title = re.sub(r'[\\/*?:"<>|]', "_", info.get("title","video"))
    except Exception as e:
        print("Meta error:", e)
        return jsonify(error="Could not fetch video info"), 500

    # Build download command
    out_tpl = os.path.join(DOWNLOAD_DIR, f"{title}.%(ext)s")
    cmd = [YTDLP_PATH, url, "-o", out_tpl]
    if format_type == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    else:
        cmd += ["-S", "ext"]  # prefer mp4 > webm > etc.

    # Run it
    try:
        print("Running:", cmd)
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = e.stderr or str(e)
        print("Download failed:", err)
        if "Sign in to confirm you’re not a bot" in err:
            return jsonify(
                error="That video requires YouTube login. Try a public video or refresh your link."
            ), 400
        return jsonify(error="Download failed"), 500

    # 5) Locate the downloaded file
    files = sorted(
        os.listdir(DOWNLOAD_DIR),
        key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_DIR, f)),
        reverse=True
    )
    if not files:
        return jsonify(error="No file found"), 500

    return jsonify(file_url=f"/file/{files[0]}")

@app.route('/file/<filename>')
def serve_file(filename):
    return send_file(
        os.path.join(DOWNLOAD_DIR, filename),
        as_attachment=True,
        download_name=filename
    )

if __name__=="__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)