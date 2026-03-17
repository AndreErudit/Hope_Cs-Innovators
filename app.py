from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
import os
from werkzeug.utils import secure_filename
from google import genai  # Google Gemini GenAI

# ===========================
# Configuration Flask
# ===========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# Configuration upload fichiers
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ===========================
# Fonctions utilitaires
# ===========================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ===========================
# Routes
# ===========================

# Page d'accueil
@app.route("/")
def home():
    return "Hello Hope CS Innovators!"

# Chat IA
@app.route("/ai", methods=["POST"])
def ai():
    user_message = request.form.get("message", "")
    if not user_message:
        return "Aucun message reçu", 400

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=user_message
    )
    return response.text

# Upload de fichiers
@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("Aucun fichier sélectionné")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("Nom de fichier vide")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            flash("Fichier téléchargé avec succès !")
            return redirect(url_for("uploaded_file", filename=filename))
    return '''
    <!doctype html>
    <title>Upload fichier</title>
    <h1>Uploader un fichier</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

# Afficher fichier uploadé
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Vote étudiant
votes = {}  # simple dictionnaire {option: nombre_de_votes}

@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        option = request.form.get("option")
        if not option:
            flash("Aucune option sélectionnée")
            return redirect(request.url)
        votes[option] = votes.get(option, 0) + 1
        flash(f"Vote enregistré pour {option} !")
        return redirect(url_for("vote_results"))
    return '''
    <!doctype html>
    <title>Vote étudiant</title>
    <h1>Votez pour votre option</h1>
    <form method=post>
      <input type=text name=option placeholder="Entrez votre option">
      <input type=submit value=Voter>
    </form>
    '''

# Afficher les résultats de vote
@app.route("/vote/results")
def vote_results():
    result_html = "<h1>Résultats des votes</h1>"
    for option, count in votes.items():
        result_html += f"<p>{option} : {count} votes</p>"
    return result_html

# ===========================
# Lancement de l'application
# ===========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render fournit le port
    app.run(host="0.0.0.0", port=port)