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
            # Pobranie info o filmie, aby zdobyć tytuł
            ydl_opts_info = {'quiet': True, 'skip_download': True}
            with YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(link, download=False)
                title = info.get('title', 'unknown')
                title_cleaned = clean_title(title)

            # Opcje do pobrania automatycznych napisów w formacie vtt
            ydl_opts_subs = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['pl-orig'],  # lub inny język
                'skip_download': True,
                'outtmpl': os.path.join(folder, f"{title_cleaned}.%(ext)s"),
                'convert_subtitles': 'vtt',
                'quiet': True,
            }

            with YoutubeDL(ydl_opts_subs) as ydl:
                ydl.download([link])

            # Znajdź pobrany plik vtt
            files = [f for f in os.listdir(folder) if f.endswith(".vtt")]
            files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
            if files:
                vtt_file = os.path.join(folder, files[0])

                with open(vtt_file, "r", encoding="utf-8") as file:
                    content = file.readlines()

                # Przetwarzanie zawartości napisów (czyszczenie)
                content = [line.strip() for line in content if line.strip()]
                content = [
                    line for line in content
                    if not re.match(r"^(WEBVTT|Kind:.*|Language:.*|\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3})", line)
                ]
                content = [re.sub(r"</?c>|<\d{2}:\d{2}:\d{2}\.\d{3}>", "", line) for line in content]
                content = list(dict.fromkeys(content))  # usunięcie duplikatów

                txt_file = os.path.join(folder, f"{title_cleaned}.txt")
                with open(txt_file, "w", encoding="utf-8") as file:
                    file.write("\n".join(content))

                os.remove(vtt_file)

                flash(f"Przetwarzanie zakończone! Plik zapisano jako: {txt_file}", "success")
            else:
                flash("Błąd: Nie znaleziono pliku VTT!", "danger")

        except Exception as e:
            flash(f"Wystąpił problem: {e}", "danger")

        return redirect(url_for("index"))

    return render_template("index.html")
