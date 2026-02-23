# ================================================================
# volunteer_routes.py  — FULL COMBINED VERSION
# Register as:  app.register_blueprint(volunteer_bp)
# ================================================================

import os
import uuid
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import mysql
from functools import wraps

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='/volunteer')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# ================================================================
# AUTH GUARD
# ================================================================
def volunteer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'volunteer_id' not in session:
            return redirect('/volunteer/login')
        return f(*args, **kwargs)
    return decorated


# ================================================================
# LOGIN
# ================================================================
@volunteer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT volunteer_id, password FROM volunteer WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()
        cur.close()

        if not user:
            flash("Invalid email or password.", "error")
            return redirect(url_for('volunteer.login'))

        stored_password = user[1]

        valid = check_password_hash(stored_password, password)

        if not valid:
            flash("Invalid email or password.", "error")
            return redirect(url_for('volunteer.login'))

        session['volunteer_id'] = user[0]
        flash("Login successful!", "success")
        return redirect(url_for('volunteer.dashboard'))

    return render_template('login.html')


# ================================================================
# DASHBOARD
# ================================================================
@volunteer_bp.route('/dashboard')
@volunteer_required
def dashboard():
    vid = session['volunteer_id']
    cur = mysql.connection.cursor()

    # ---- Volunteer info ----
    cur.execute("""
        SELECT first_name, last_name, email, phone, gender,
               skills, profile_picture
        FROM volunteer
        WHERE volunteer_id = %s
    """, (vid,))
    vol = cur.fetchone()

    first_name, last_name, email, phone, gender, skills_str, profile_picture = vol

    volunteer_skills = [s.strip() for s in (skills_str or '').split(',') if s.strip()]
    skills_count     = len(volunteer_skills)

    # ---- Activities NOT joined ----
    cur.execute("""
        SELECT activity_id, name, type, start_date, required_skills
        FROM activity
        WHERE activity_id NOT IN (
            SELECT activity_id FROM volunteer_activity
            WHERE volunteer_id = %s
        )
        ORDER BY start_date
    """, (vid,))
    raw_activities = cur.fetchall()

    activities = []
    for act in raw_activities:
        act_id, name, atype, start_date, req_skills_str = act
        req_skills = [s.strip() for s in (req_skills_str or '').split(',') if s.strip()]

        if req_skills:
            matched  = [s for s in req_skills if s in volunteer_skills]
            eligible = (skills_count >= 2) and (len(matched) == len(req_skills))
            missing  = [s for s in req_skills if s not in volunteer_skills]
        else:
            eligible = skills_count >= 2
            missing  = []

        activities.append({
            'id':         act_id,
            'name':       name,
            'type':       atype,
            'date':       start_date,
            'req_skills': req_skills,
            'eligible':   eligible,
            'missing':    missing,
        })

    # ---- Joined activities ----
    cur.execute("""
        SELECT a.name, a.start_date, va.role,
               va.attendance, va.performance_rating
        FROM volunteer_activity va
        JOIN activity a ON va.activity_id = a.activity_id
        WHERE va.volunteer_id = %s
        ORDER BY a.start_date DESC
    """, (vid,))
    joined = cur.fetchall()
    cur.close()

    return render_template(
        'volunteer/dashboard.html',
        activities       = activities,
        joined           = joined,
        volunteer_skills = volunteer_skills,
        skills_count     = skills_count,
        first_name       = first_name,
        last_name        = last_name,
        email            = email,
        phone            = phone or '',
        gender           = gender or '',
        profile_picture  = profile_picture,
    )


# ================================================================
# UPDATE SKILLS
# ================================================================
@volunteer_bp.route('/skills/update', methods=['POST'])
@volunteer_required
def update_skills():
    vid = session['volunteer_id']
    raw = request.form.get('skills', '')

    skills_list = list(dict.fromkeys(
        s.strip().title() for s in raw.split(',') if s.strip()
    ))
    skills_str = ', '.join(skills_list)

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE volunteer SET skills=%s WHERE volunteer_id=%s",
        (skills_str, vid)
    )
    mysql.connection.commit()
    cur.close()

    if len(skills_list) < 2:
        flash('Skills saved! Add at least 2 skills to join activities.', 'warning')
    else:
        flash(f'{len(skills_list)} skills saved successfully!', 'success')

    return redirect(url_for('volunteer.dashboard'))


# ================================================================
# UPDATE PROFILE PICTURE
# ================================================================
@volunteer_bp.route('/profile/picture', methods=['POST'])
@volunteer_required
def update_picture():
    vid = session['volunteer_id']

    if 'profile_picture' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    file = request.files['profile_picture']

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    ext = file.filename.rsplit('.', 1)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        flash('Invalid file type.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    filename = f"avatar_{vid}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

    # Delete old picture from disk if it exists
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT profile_picture FROM volunteer WHERE volunteer_id = %s", (vid,)
    )
    old = cur.fetchone()
    if old and old[0]:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old[0])
        if os.path.exists(old_path):
            os.remove(old_path)

    file.save(filepath)

    cur.execute(
        "UPDATE volunteer SET profile_picture=%s WHERE volunteer_id=%s",
        (filename, vid)
    )
    mysql.connection.commit()
    cur.close()

    flash('Profile picture updated successfully!', 'success')
    return redirect(url_for('volunteer.dashboard'))


# ================================================================
# CHANGE PASSWORD
# ================================================================
@volunteer_bp.route('/profile/password', methods=['POST'])
@volunteer_required
def change_password():
    vid        = session['volunteer_id']
    current_pw = request.form.get('current_password', '').strip()
    new_pw     = request.form.get('new_password', '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()

    if not current_pw or not new_pw or not confirm_pw:
        flash('All password fields are required.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    if new_pw != confirm_pw:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    if len(new_pw) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('volunteer.dashboard'))

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT password FROM volunteer WHERE volunteer_id=%s", (vid,)
    )
    stored = cur.fetchone()[0]

    valid = check_password_hash(stored, current_pw)

    if not valid:
        flash('Current password incorrect.', 'error')
        cur.close()
        return redirect(url_for('volunteer.dashboard'))

    cur.execute(
        "UPDATE volunteer SET password=%s WHERE volunteer_id=%s",
        (generate_password_hash(new_pw), vid)
    )
    mysql.connection.commit()
    cur.close()

    flash('Password changed successfully!', 'success')
    return redirect(url_for('volunteer.dashboard'))


# ================================================================
# JOIN ACTIVITY
# ================================================================
@volunteer_bp.route('/join/<int:activity_id>')
@volunteer_required
def join_activity(activity_id):
    vid = session['volunteer_id']
    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT skills FROM volunteer WHERE volunteer_id=%s", (vid,)
    )
    volunteer_skills = [
        s.strip() for s in (cur.fetchone()[0] or '').split(',') if s.strip()
    ]

    if len(volunteer_skills) < 2:
        flash('Add at least 2 skills before joining.', 'error')
        cur.close()
        return redirect(url_for('volunteer.dashboard'))

    cur.execute(
        "SELECT required_skills FROM activity WHERE activity_id=%s", (activity_id,)
    )
    act_row = cur.fetchone()

    if not act_row:
        flash('Activity not found.', 'error')
        cur.close()
        return redirect(url_for('volunteer.dashboard'))

    req_skills = [s.strip() for s in (act_row[0] or '').split(',') if s.strip()]
    missing    = [s for s in req_skills if s not in volunteer_skills]

    if missing:
        flash(f'Missing required skills: {", ".join(missing)}.', 'error')
        cur.close()
        return redirect(url_for('volunteer.dashboard'))

    try:
        cur.execute(
            "INSERT INTO volunteer_activity (volunteer_id, activity_id) VALUES (%s,%s)",
            (vid, activity_id)
        )
        mysql.connection.commit()
        flash('Successfully joined the activity!', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('Already joined this activity.', 'warning')

    cur.close()
    return redirect(url_for('volunteer.dashboard'))