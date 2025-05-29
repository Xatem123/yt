from flask import Flask, render_template, request, redirect, url_for, flash
import os
import re
from yt_dlp import YoutubeDL

app = Flask(__name__)
app.secret_key = "supersecretkey"

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def clean_title(title):
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in title)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        link = request.form.get("link", "").strip()
        folder = DOWNLOAD_FOLDER

        if not link:
            flash("Wprowadź link do filmu YouTube.", "warning")
            return redirect(url_for("index"))

        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['pl-orig'],
                'subtitlesformat': 'vtt',
                'outtmpl': os.path.join(folder, '%(title)s.%(ext)s'),
            }
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(link, download=False)
                title = info_dict.get('title', 'video')
                title_cleaned = clean_title(title)

                # Pobierz napisy (automatyczne)
                ydl_opts['outtmpl'] = os.path.join(folder, f"{title_cleaned}.%(ext)s")
                ydl_opts['skip_download'] = True
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['pl-orig']
                ydl_opts['subtitlesformat'] = 'vtt'

                with YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([link])

            # Szukamy najnowszego pliku .vtt
            files = [f for f in os.listdir(folder) if f.endswith(".vtt")]
            files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)

            if not files:
                flash("Błąd: Nie znaleziono pliku VTT!", "danger")
                return redirect(url_for("index"))

            vtt_file = os.path.join(folder, files[0])

            with open(vtt_file, "r", encoding="utf-8") as file:
                content = file.readlines()

            content = [line.strip() for line in content if line.strip()]
            content = [
                line for line in content
                if not re.match(r"^(WEBVTT|Kind:.*|Language:.*|\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3})", line)
            ]
            content = [re.sub(r"</?c>|<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line) for line in content]
            content = list(dict.fromkeys(content))

            txt_file = os.path.join(folder, f"{title_cleaned}.txt")
            with open(txt_file, "w", encoding="utf-8") as file:
                file.writelines("\n".join(content))

            os.remove(vtt_file)

            flash(f"Przetwarzanie zakończone! Plik zapisano jako: {txt_file}", "success")

        except Exception as e:
            flash(f"Wystąpił problem: {e}", "danger")

        return redirect(url_for("index"))

    return render_template("index.html")
