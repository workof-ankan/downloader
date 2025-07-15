from flask import Flask, request, jsonify, send_from_directory, send_file
import subprocess
import os
import time

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
YTDLP_PATH = "yt-dlp"  # adjust if path is different
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get("url")
    format_type = data.get("format")

    if not url or format_type not in ["audio", "video"]:
        return jsonify({"error": "Invalid input"}), 400

    # Clean downloads folder before download (optional)
    for f in os.listdir(DOWNLOAD_DIR):
        os.remove(os.path.join(DOWNLOAD_DIR, f))

    output_template = os.path.join(DOWNLOAD_DIR, "%(title).80s.%(ext)s")
    cmd = [YTDLP_PATH, url, "-o", output_template]

    if format_type == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    else:
        cmd += ["--format", "mp4"]

    try:
        print("Running command:", cmd)
        subprocess.run(cmd, check=True)

        # Find the newest file in the downloads folder
        downloaded_files = sorted(
            [f for f in os.listdir(DOWNLOAD_DIR)],
            key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_DIR, f)),
            reverse=True
        )
        if not downloaded_files:
            return jsonify({"error": "No file downloaded"}), 500

        latest_file = downloaded_files[0]
        return jsonify({"file_url": f"/file/{latest_file}"})
    except subprocess.CalledProcessError as e:
        print("Download failed:", e)
        return jsonify({"error": "Download failed"}), 500


@app.route('/file/<filename>')
def serve_file(filename):
    return send_file(
        os.path.join(DOWNLOAD_DIR, filename),
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

