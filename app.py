from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_socketio import SocketIO, send
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

# ========================
# CONFIG
# ========================
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["UPLOAD_FOLDER"] = "uploads"

os.makedirs("uploads", exist_ok=True)

db = SQLAlchemy(app)
socketio = SocketIO(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ========================
# MODELS
# ========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    online = db.Column(db.Boolean, default=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300))
    user = db.Column(db.String(50))
    read = db.Column(db.Boolean, default=False)

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    user = db.Column(db.String(50))

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200))
    option1 = db.Column(db.String(100))
    option2 = db.Column(db.String(100))
    votes1 = db.Column(db.Integer, default=0)
    votes2 = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========================
# ROUTES
# ========================
@app.route("/")
def index():
    return render_template("index.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            user.online = True
            db.session.commit()
            return redirect("/dashboard")
    return render_template("login.html")

# LOGOUT
@app.route("/logout")
@login_required
def logout():
    current_user.online = False
    db.session.commit()
    logout_user()
    return redirect("/")

# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    users = User.query.all()
    return render_template("dashboard.html", users=users)

# ========================
# CHAT
# ========================
@app.route("/chat")
@login_required
def chat():
    messages = Message.query.all()
    return render_template("chat.html", messages=messages)

@socketio.on("message")
def handle_message(msg):
    m = Message(content=msg, user=current_user.name)
    db.session.add(m)
    db.session.commit()
    send({"msg": msg, "user": current_user.name, "id": m.id}, broadcast=True)

# ========================
# FILE UPLOAD
# ========================
@app.route("/resources", methods=["GET","POST"])
@login_required
def resources():
    if request.method == "POST":
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join("uploads", filename))

        r = Resource(filename=filename, user=current_user.name)
        db.session.add(r)
        db.session.commit()

    resources = Resource.query.all()
    return render_template("resources.html", resources=resources)

@app.route("/download/<filename>")
@login_required
def download(filename):
    return send_from_directory("uploads", filename)

# ========================
# VOTE
# ========================
@app.route("/vote", methods=["GET","POST"])
@login_required
def vote():
    if request.method == "POST":
        v = Vote(
            question=request.form["question"],
            option1=request.form["opt1"],
            option2=request.form["opt2"]
        )
        db.session.add(v)
        db.session.commit()

    votes = Vote.query.all()
    return render_template("vote.html", votes=votes)

@app.route("/vote_action/<int:id>/<choice>")
@login_required
def vote_action(id, choice):
    v = Vote.query.get(id)
    if choice == "1":
        v.votes1 += 1
    else:
        v.votes2 += 1
    db.session.commit()
    return redirect("/vote")

# ========================
# IA (OpenAI)
# ========================
from google import genai

client = genai.Client(api_key="AIzaSyDboQYIaDtU6Y8wdEbWW2LjLTeLNFlopiA")

@app.route("/ai", methods=["POST"])
def ai():
    user_message = request.form["message"]

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=user_message
    )

    
    answer = response["choices"][0]["message"]["content"]
    return render_template("ai.html", answer=answer)

# ========================
# RUN
# ========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app)