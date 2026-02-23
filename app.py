from flask import Flask, render_template, request, redirect, session, flash
from config import Config
from db import mysql
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os

from admin.routes import admin_bp
from volunteer.routes import volunteer_bp
from organization.routes import org_bp

app = Flask(__name__)
app.config.from_object(Config)

# ==========================
# FILE UPLOAD CONFIG
# ==========================
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'avatars')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB max upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mysql.init_app(app)

# ==========================
# Register blueprints
# ==========================
app.register_blueprint(admin_bp,      url_prefix="/admin")
app.register_blueprint(volunteer_bp,  url_prefix="/volunteer")
app.register_blueprint(org_bp,        url_prefix="/organization")

# ==========================
# INDEX
# ==========================
@app.route("/")
def index():
    return render_template("index.html")

# ==========================
# LOGIN
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        # reCAPTCHA verification
        recaptcha_response = request.form.get("g-recaptcha-response")
        payload = {
            "secret": app.config["RECAPTCHA_SECRET"],
            "response": recaptcha_response
        }
        r = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=payload
        )
        result = r.json()

        if not result.get("success"):
            flash("reCAPTCHA verification failed", "error")
            return redirect("/login")

        role     = request.form["role"]
        email    = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        if role == "volunteer":
            cur.execute(
                "SELECT volunteer_id, password FROM volunteer WHERE email=%s",
                (email,)
            )
        else:
            cur.execute(
                "SELECT org_id, password FROM organization WHERE email=%s",
                (email,)
            )

        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["role"] = role
            if role == "volunteer":
                session["volunteer_id"] = user[0]
            else:
                session["org_id"] = user[0]
            return redirect(f"/{role}/dashboard")

        flash("Invalid email or password", "error")
        return redirect("/login")

    return render_template("login.html")

# ==========================
# REGISTER
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # reCAPTCHA verification
        recaptcha_response = request.form.get("g-recaptcha-response")
        payload = {
            "secret": app.config["RECAPTCHA_SECRET"],
            "response": recaptcha_response
        }
        r = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=payload
        )
        result = r.json()

        if not result.get("success"):
            flash("reCAPTCHA verification failed", "error")
            return redirect("/register")

        role     = request.form["role"]
        email    = request.form["email"]
        password = generate_password_hash(request.form["password"])

        cur = mysql.connection.cursor()

        # ==========================
        # CHECK DUPLICATE EMAIL
        # ==========================
        if role == "volunteer":
            cur.execute("SELECT volunteer_id FROM volunteer WHERE email=%s", (email,))
        else:
            cur.execute("SELECT org_id FROM organization WHERE email=%s", (email,))

        if cur.fetchone():
            cur.close()
            flash("Email already registered", "warning")
            return redirect("/register")

        # ==========================
        # INSERT DATA
        # ==========================
        if role == "volunteer":
            first_name = request.form["first_name"]
            last_name  = request.form["last_name"]
            gender     = request.form.get("gender")
            phone      = request.form.get("phone")

            cur.execute("""
                INSERT INTO volunteer
                (first_name, last_name, email, password, gender, phone)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, email, password, gender, phone))

        else:
            name           = request.form["name"]
            representative = request.form.get("representative")
            phone          = request.form.get("org_phone")
            address        = request.form.get("address")

            cur.execute("""
                INSERT INTO organization
                (name, email, password, phone, address, representative)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, password, phone, address, representative))

        mysql.connection.commit()
        cur.close()

        flash("Registration successful. Please login.", "success")
        return redirect("/login")

    return render_template("register.html")

# ==========================
# LOGOUT
# ==========================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/")

# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    app.run(debug=True)