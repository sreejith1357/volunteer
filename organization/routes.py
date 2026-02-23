# ================================================================
# organization/routes.py  — FULL UPDATED VERSION
# ================================================================

import os
import uuid
from flask import (
    Blueprint, render_template, request,
    redirect, session, flash, current_app
)
from db import mysql
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

org_bp = Blueprint("organization", __name__)


# ── Auth guard ───────────────────────────────────────────────────
def org_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "organization":
            flash("Please log in as an organization.", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


# ── Email helper ─────────────────────────────────────────────────
def send_notification_email(to_email, volunteer_name, activity_name, position_title, reg_close):
    try:
        from flask_mail import Message
        from app import mail
        msg = Message(
            subject=f"New Volunteer Position: {position_title} — {activity_name}",
            recipients=[to_email],
            html=f"""
            <h2>New Volunteer Opportunity!</h2>
            <p>Hi {volunteer_name},</p>
            <p>A new position matching your skills is open:</p>
            <ul>
                <li><strong>Activity:</strong> {activity_name}</li>
                <li><strong>Position:</strong> {position_title}</li>
                <li><strong>Registration closes:</strong> {reg_close}</li>
            </ul>
            <p>Log in to your dashboard to apply.</p>
            """
        )
        mail.send(msg)
    except Exception:
        pass


# ================================================================
# LOGIN
# ================================================================
@org_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT org_id, password FROM organization WHERE email=%s", (email,)
        )
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["role"]    = "organization"
            return redirect("/organization/dashboard")

        flash("Invalid email or password", "error")
        return redirect("/organization/login")

    return render_template("login.html")


# ================================================================
# DASHBOARD
# ================================================================
@org_bp.route("/dashboard")
@org_required
def dashboard():
    org_id = session["user_id"]
    cur    = mysql.connection.cursor()

    # Full org details for profile modal pre-fill
    cur.execute("""
        SELECT name, email, phone, address, representative, profile_picture
        FROM organization WHERE org_id=%s
    """, (org_id,))
    org = cur.fetchone()

    org_name            = org[0] if org else "Organization"
    org_email           = org[1] if org else ""
    org_phone           = org[2] if org else ""
    org_address         = org[3] if org else ""
    org_representative  = org[4] if org else ""
    org_picture         = org[5] if org else None

    # Activities with position + volunteer counts
    cur.execute("""
        SELECT a.activity_id, a.name, a.type, a.start_date, a.end_date,
               a.place, a.description, a.reg_open, a.reg_close,
               COUNT(DISTINCT ap.position_id) AS position_count,
               COUNT(DISTINCT va.id)           AS volunteer_count
        FROM activity a
        LEFT JOIN activity_position ap ON a.activity_id = ap.activity_id
        LEFT JOIN volunteer_activity va ON a.activity_id = va.activity_id
        WHERE a.org_id = %s
        GROUP BY a.activity_id
        ORDER BY a.start_date DESC
    """, (org_id,))
    activities = cur.fetchall()

    cur.close()
    return render_template(
        "organization/dashboard.html",
        activities         = activities,
        org_name           = org_name,
        org_email          = org_email,
        org_phone          = org_phone,
        org_address        = org_address,
        org_representative = org_representative,
        org_picture        = org_picture,
        now                = datetime.now(),
    )


# ================================================================
# UPDATE PROFILE  (name, phone, address, representative)
# ================================================================
@org_bp.route("/profile/update", methods=["POST"])
@org_required
def update_profile():
    org_id         = session["user_id"]
    name           = request.form.get("name", "").strip()
    phone          = request.form.get("phone", "").strip()
    address        = request.form.get("address", "").strip()
    representative = request.form.get("representative", "").strip()

    if not name:
        flash("Organization name is required.", "error")
        return redirect("/organization/dashboard")

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE organization
        SET name=%s, phone=%s, address=%s, representative=%s
        WHERE org_id=%s
    """, (name, phone, address, representative, org_id))
    mysql.connection.commit()
    cur.close()

    flash("Profile updated successfully.", "success")
    return redirect("/organization/dashboard")


# ================================================================
# UPDATE PROFILE PICTURE
# ================================================================
@org_bp.route("/profile/picture", methods=["POST"])
@org_required
def update_picture():
    org_id = session["user_id"]

    if "picture" not in request.files:
        flash("No file selected.", "error")
        return redirect("/organization/dashboard")

    file = request.files["picture"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect("/organization/dashboard")

    allowed = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        flash("Invalid file type. Use PNG, JPG, GIF or WebP.", "error")
        return redirect("/organization/dashboard")

    # Delete old picture
    cur = mysql.connection.cursor()
    cur.execute("SELECT profile_picture FROM organization WHERE org_id=%s", (org_id,))
    old = cur.fetchone()
    if old and old[0]:
        old_path = os.path.join(current_app.config.get("UPLOAD_FOLDER", "static/uploads/avatars"), old[0])
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new picture
    filename = f"org_{org_id}_{uuid.uuid4().hex[:8]}.{ext}"
    upload_dir = current_app.config.get("UPLOAD_FOLDER", "static/uploads/avatars")
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))

    cur.execute("UPDATE organization SET profile_picture=%s WHERE org_id=%s", (filename, org_id))
    mysql.connection.commit()
    cur.close()

    flash("Profile picture updated.", "success")
    return redirect("/organization/dashboard")


# ================================================================
# REMOVE PROFILE PICTURE
# ================================================================
@org_bp.route("/profile/remove_picture", methods=["POST"])
@org_required
def remove_picture():
    org_id = session["user_id"]
    cur = mysql.connection.cursor()
    cur.execute("SELECT profile_picture FROM organization WHERE org_id=%s", (org_id,))
    row = cur.fetchone()
    if row and row[0]:
        old_path = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "static/uploads/avatars"), row[0]
        )
        if os.path.exists(old_path):
            os.remove(old_path)
    cur.execute("UPDATE organization SET profile_picture=NULL WHERE org_id=%s", (org_id,))
    mysql.connection.commit()
    cur.close()
    flash("Profile picture removed.", "success")
    return redirect("/organization/dashboard")


# ================================================================
# CHANGE PASSWORD
# ================================================================
@org_bp.route("/profile/password", methods=["POST"])
@org_required
def change_password():
    org_id      = session["user_id"]
    current_pw  = request.form.get("current_password", "")
    new_pw      = request.form.get("new_password", "")
    confirm_pw  = request.form.get("confirm_password", "")

    if not current_pw or not new_pw or not confirm_pw:
        flash("All password fields are required.", "error")
        return redirect("/organization/dashboard")

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect("/organization/dashboard")

    if len(new_pw) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect("/organization/dashboard")

    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM organization WHERE org_id=%s", (org_id,))
    row = cur.fetchone()

    if not row or not check_password_hash(row[0], current_pw):
        flash("Current password is incorrect.", "error")
        cur.close()
        return redirect("/organization/dashboard")

    cur.execute(
        "UPDATE organization SET password=%s WHERE org_id=%s",
        (generate_password_hash(new_pw), org_id)
    )
    mysql.connection.commit()
    cur.close()

    flash("Password changed successfully.", "success")
    return redirect("/organization/dashboard")


# ================================================================
# CREATE ACTIVITY  (with positions + registration window)
# ================================================================
@org_bp.route("/create_activity", methods=["POST"])
@org_required
def create_activity():
    org_id      = session["user_id"]
    name        = request.form["name"]
    type_       = request.form["type"]
    place       = request.form["place"]
    start       = request.form["start_date"]
    end         = request.form["end_date"]
    description = request.form.get("description", "")
    reg_open    = request.form.get("reg_open")  or None
    reg_close   = request.form.get("reg_close") or None

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO activity
        (name, type, place, start_date, end_date, org_id,
         description, reg_open, reg_close)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (name, type_, place, start, end, org_id,
          description, reg_open, reg_close))
    mysql.connection.commit()
    activity_id = cur.lastrowid

    titles  = request.form.getlist("position_title[]")
    skills  = request.form.getlist("position_skills[]")
    slots   = request.form.getlist("position_slots[]")

    eligible_volunteers = {}

    for i, title in enumerate(titles):
        if not title.strip():
            continue
        req_skills = skills[i].strip()  if i < len(skills)  else ''
        num_slots  = int(slots[i])      if i < len(slots) and slots[i].isdigit() else 1

        cur.execute("""
            INSERT INTO activity_position
            (activity_id, title, required_skills, slots)
            VALUES (%s, %s, %s, %s)
        """, (activity_id, title.strip(), req_skills, num_slots))
        mysql.connection.commit()
        position_id = cur.lastrowid

        req_list = [s.strip().lower() for s in req_skills.split(',') if s.strip()]

        if req_list:
            cur.execute("""
                SELECT volunteer_id, email,
                       CONCAT(first_name, ' ', last_name) AS full_name,
                       skills
                FROM volunteer
                WHERE skills IS NOT NULL AND skills != ''
            """)
            all_vols = cur.fetchall()

            matched = []
            for vol in all_vols:
                vol_id, vol_email, vol_name, vol_skills_str = vol
                vol_skills = [s.strip().lower() for s in (vol_skills_str or '').split(',') if s.strip()]
                if all(r in vol_skills for r in req_list):
                    matched.append((vol_id, vol_email, vol_name))
            eligible_volunteers[position_id] = matched
        else:
            cur.execute("""
                SELECT volunteer_id, email,
                       CONCAT(first_name, ' ', last_name) AS full_name
                FROM volunteer
                WHERE LENGTH(skills) - LENGTH(REPLACE(skills, ',', '')) >= 1
            """)
            eligible_volunteers[position_id] = cur.fetchall()

    for position_id, volunteers in eligible_volunteers.items():
        cur.execute(
            "SELECT title, required_skills FROM activity_position WHERE position_id=%s",
            (position_id,)
        )
        pos = cur.fetchone()
        pos_title      = pos[0] if pos else "Volunteer"
        pos_skills_str = pos[1] if pos else ""

        for vol_id, vol_email, vol_name in volunteers:
            cur.execute("""
                INSERT INTO notification
                (volunteer_id, activity_id, message)
                VALUES (%s, %s, %s)
            """, (
                vol_id, activity_id,
                f"New position open: '{pos_title}' for '{name}'. "
                f"Required skills: {pos_skills_str or 'None'}. "
                f"Registration closes: {reg_close or 'Open'}."
            ))
            mysql.connection.commit()
            send_notification_email(vol_email, vol_name, name, pos_title, reg_close or "Open")

    cur.close()
    flash(f"Activity '{name}' created with {len(titles)} position(s)!", "success")
    return redirect("/organization/dashboard")


# ================================================================
# VIEW VOLUNTEERS  (skill-sorted by position)
# ================================================================
@org_bp.route("/volunteers/<int:activity_id>")
@org_required
def volunteers(activity_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT a.name, a.type, a.place, a.start_date, a.end_date,
               a.description, a.reg_open, a.reg_close
        FROM activity a WHERE a.activity_id = %s
    """, (activity_id,))
    activity = cur.fetchone()

    cur.execute("""
        SELECT position_id, title, required_skills, slots, filled
        FROM activity_position
        WHERE activity_id = %s
        ORDER BY position_id
    """, (activity_id,))
    positions = cur.fetchall()

    volunteers_by_position = {}
    for pos in positions:
        pos_id = pos[0]
        cur.execute("""
            SELECT va.id, vol.first_name, vol.last_name,
                   vol.email, vol.phone, vol.skills,
                   va.attendance, va.performance_rating, va.status
            FROM volunteer_activity va
            JOIN volunteer vol ON va.volunteer_id = vol.volunteer_id
            WHERE va.activity_id = %s AND va.position_id = %s
            ORDER BY vol.first_name
        """, (activity_id, pos_id))
        volunteers_by_position[pos_id] = cur.fetchall()

    cur.execute("""
        SELECT va.id, vol.first_name, vol.last_name,
               vol.email, vol.phone, vol.skills,
               va.attendance, va.performance_rating, va.status
        FROM volunteer_activity va
        JOIN volunteer vol ON va.volunteer_id = vol.volunteer_id
        WHERE va.activity_id = %s AND va.position_id IS NULL
        ORDER BY vol.first_name
    """, (activity_id,))
    unassigned = cur.fetchall()

    eligible_by_position = {}
    for pos in positions:
        pos_id     = pos[0]
        req_skills = [s.strip().lower() for s in (pos[2] or '').split(',') if s.strip()]

        cur.execute("""
            SELECT vol.volunteer_id, vol.first_name, vol.last_name,
                   vol.email, vol.skills
            FROM volunteer vol
            WHERE vol.volunteer_id NOT IN (
                SELECT volunteer_id FROM volunteer_activity
                WHERE activity_id = %s
            )
            AND vol.skills IS NOT NULL AND vol.skills != ''
        """, (activity_id,))
        all_available = cur.fetchall()

        matched = []
        for vol in all_available:
            vol_id, fn, ln, email, skills_str = vol
            vol_skills = [s.strip().lower() for s in (skills_str or '').split(',') if s.strip()]
            if not req_skills or all(r in vol_skills for r in req_skills):
                match_count = sum(1 for r in req_skills if r in vol_skills)
                matched.append((vol_id, fn, ln, email, skills_str, match_count))

        matched.sort(key=lambda x: x[5], reverse=True)
        eligible_by_position[pos_id] = matched

    cur.close()
    return render_template(
        "organization/volunteers.html",
        activity               = activity,
        activity_id            = activity_id,
        positions              = positions,
        volunteers_by_position = volunteers_by_position,
        unassigned             = unassigned,
        eligible_by_position   = eligible_by_position,
        now                    = datetime.now(),
    )


# ================================================================
# UPDATE VOLUNTEER (attendance + rating)
# ================================================================
@org_bp.route("/update/<int:id>", methods=["POST"])
@org_required
def update(id):
    attendance = request.form["attendance"]
    rating     = request.form["rating"]

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE volunteer_activity
        SET attendance=%s, performance_rating=%s
        WHERE id=%s
    """, (attendance, rating, id))
    mysql.connection.commit()
    cur.close()

    flash("Volunteer record updated.", "success")
    return redirect(request.referrer)


# ================================================================
# NOTIFY VOLUNTEERS FOR A POSITION (manual re-notify)
# ================================================================
@org_bp.route("/notify/<int:activity_id>/<int:position_id>", methods=["POST"])
@org_required
def notify_position(activity_id, position_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT ap.title, ap.required_skills, a.name, a.reg_close
        FROM activity_position ap
        JOIN activity a ON ap.activity_id = a.activity_id
        WHERE ap.position_id = %s
    """, (position_id,))
    pos = cur.fetchone()

    if not pos:
        flash("Position not found.", "error")
        return redirect(request.referrer)

    pos_title, req_skills_str, act_name, reg_close = pos
    req_list = [s.strip().lower() for s in (req_skills_str or '').split(',') if s.strip()]

    cur.execute("""
        SELECT volunteer_id, email,
               CONCAT(first_name,' ',last_name), skills
        FROM volunteer
        WHERE skills IS NOT NULL AND skills != ''
    """)
    all_vols = cur.fetchall()

    notified = 0
    for vol_id, vol_email, vol_name, skills_str in all_vols:
        vol_skills = [s.strip().lower() for s in (skills_str or '').split(',') if s.strip()]
        if not req_list or all(r in vol_skills for r in req_list):
            cur.execute("""
                INSERT INTO notification (volunteer_id, activity_id, message)
                VALUES (%s, %s, %s)
            """, (
                vol_id, activity_id,
                f"Reminder: Position '{pos_title}' is still open for '{act_name}'. "
                f"Registration closes: {reg_close or 'Open'}."
            ))
            mysql.connection.commit()
            send_notification_email(vol_email, vol_name, act_name, pos_title, reg_close or "Open")
            notified += 1

    cur.close()
    flash(f"Notified {notified} eligible volunteer(s).", "success")
    return redirect(request.referrer)