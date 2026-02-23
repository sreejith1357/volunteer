from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from db import mysql
from datetime import datetime

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


# ─────────────────────────────────────────
# Auth guard (replaces repeated if checks)
# ─────────────────────────────────────────
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()

        if admin and check_password_hash(admin[2], password):
            session['admin_id']   = admin[0]
            session['admin_name'] = admin[1]
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash("Invalid Username or Password", "danger")

    return render_template('admin_login.html')


# ─────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────
@admin_bp.route('/logout')
def admin_logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('admin.admin_login'))


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM volunteer")
    volunteers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM organization")
    orgs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM activity")
    activities = cur.fetchone()[0]

    # Full volunteer list
    cur.execute("""
        SELECT volunteer_id, first_name, last_name, email,
               gender, phone, skills, profile_picture, created_at
        FROM volunteer ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    vcols = ['volunteer_id','first_name','last_name','email',
             'gender','phone','skills','profile_picture','created_at']
    volunteer_list = [dict(zip(vcols, r)) for r in rows]

    # Full organization list with activity count
    cur.execute("""
        SELECT o.org_id, o.name, o.email, o.phone,
               o.address, o.representative, o.profile_picture, o.created_at,
               COUNT(a.activity_id) AS activity_count
        FROM organization o
        LEFT JOIN activity a ON o.org_id = a.org_id
        GROUP BY o.org_id
        ORDER BY o.created_at DESC
    """)
    rows = cur.fetchall()
    ocols = ['org_id','name','email','phone','address',
             'representative','profile_picture','created_at','activity_count']
    org_list = [dict(zip(ocols, r)) for r in rows]

    # Full activity list with org name + volunteer count
    cur.execute("""
        SELECT a.activity_id, a.name, a.type, a.place,
               a.start_date, a.end_date, a.reg_open, a.reg_close,
               o.name AS org_name,
               COUNT(va.id) AS volunteer_count
        FROM activity a
        JOIN organization o ON a.org_id = o.org_id
        LEFT JOIN volunteer_activity va ON a.activity_id = va.activity_id
        GROUP BY a.activity_id
        ORDER BY a.start_date DESC
    """)
    rows = cur.fetchall()
    acols = ['activity_id','name','type','place','start_date','end_date',
             'reg_open','reg_close','org_name','volunteer_count']
    activity_list = [dict(zip(acols, r)) for r in rows]

    cur.close()
    return render_template(
        'admin_dashboard.html',
        volunteers     = volunteers,
        orgs           = orgs,
        activities     = activities,
        volunteer_list = volunteer_list,
        org_list       = org_list,
        activity_list  = activity_list,
        now            = datetime.now(),
    )


# ─────────────────────────────────────────
# VIEW VOLUNTEERS  (kept for compatibility)
# ─────────────────────────────────────────
@admin_bp.route('/volunteers')
@admin_required
def view_volunteers():
    cur = mysql.connection.cursor()
    cur.execute("SELECT volunteer_id, first_name, last_name, email, gender, phone FROM volunteer")
    volunteers = cur.fetchall()
    cur.close()
    return render_template('view_volunteers.html', volunteers=volunteers)


# ─────────────────────────────────────────
# ADD VOLUNTEER
# ─────────────────────────────────────────
@admin_bp.route('/volunteer/add', methods=['POST'])
@admin_required
def add_volunteer():
    first  = request.form.get('first_name', '').strip()
    last   = request.form.get('last_name',  '').strip()
    email  = request.form.get('email',      '').strip()
    pw     = request.form.get('password',   '')
    phone  = request.form.get('phone',      '').strip()
    gender = request.form.get('gender',     '')
    skills = request.form.get('skills',     '').strip()

    if not first or not last or not email or not pw:
        flash("First name, last name, email and password are required.", "danger")
        return redirect(url_for('admin.admin_dashboard') + '?tab=volunteers')

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO volunteer
            (first_name, last_name, email, password, phone, gender, skills)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (first, last, email,
              generate_password_hash(pw),
              phone or None, gender or None, skills))
        mysql.connection.commit()
        flash(f"Volunteer {first} {last} added successfully.", "success")
    except Exception:
        mysql.connection.rollback()
        flash("Could not add volunteer. Email may already be registered.", "danger")
    finally:
        cur.close()

    return redirect(url_for('admin.admin_dashboard') + '?tab=volunteers')


# ─────────────────────────────────────────
# DELETE VOLUNTEER
# ─────────────────────────────────────────
@admin_bp.route('/volunteer/delete/<int:volunteer_id>', methods=['POST'])
@admin_required
def delete_volunteer(volunteer_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT first_name, last_name FROM volunteer WHERE volunteer_id=%s", (volunteer_id,))
    vol = cur.fetchone()
    if vol:
        cur.execute("DELETE FROM volunteer WHERE volunteer_id=%s", (volunteer_id,))
        mysql.connection.commit()
        flash(f"Volunteer {vol[0]} {vol[1]} deleted.", "success")
    else:
        flash("Volunteer not found.", "danger")
    cur.close()
    return redirect(url_for('admin.admin_dashboard') + '?tab=volunteers')


# ─────────────────────────────────────────
# VIEW ORGANIZATIONS  (kept for compatibility)
# ─────────────────────────────────────────
@admin_bp.route('/organizations')
@admin_required
def view_organizations():
    cur = mysql.connection.cursor()
    cur.execute("SELECT org_id, name, email, phone, address, representative FROM organization")
    orgs = cur.fetchall()
    cur.close()
    return render_template('view_organizations.html', orgs=orgs)


# ─────────────────────────────────────────
# ADD ORGANIZATION
# ─────────────────────────────────────────
@admin_bp.route('/org/add', methods=['POST'])
@admin_required
def add_org():
    name   = request.form.get('name',           '').strip()
    email  = request.form.get('email',          '').strip()
    pw     = request.form.get('password',       '')
    phone  = request.form.get('phone',          '').strip()
    rep    = request.form.get('representative', '').strip()
    addr   = request.form.get('address',        '').strip()

    if not name or not email or not pw:
        flash("Name, email and password are required.", "danger")
        return redirect(url_for('admin.admin_dashboard') + '?tab=organizations')

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO organization
            (name, email, password, phone, representative, address)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email,
              generate_password_hash(pw),
              phone or None, rep or None, addr or None))
        mysql.connection.commit()
        flash(f"Organization '{name}' added successfully.", "success")
    except Exception:
        mysql.connection.rollback()
        flash("Could not add organization. Email may already be registered.", "danger")
    finally:
        cur.close()

    return redirect(url_for('admin.admin_dashboard') + '?tab=organizations')


# ─────────────────────────────────────────
# DELETE ORGANIZATION
# ─────────────────────────────────────────
@admin_bp.route('/org/delete/<int:org_id>', methods=['POST'])
@admin_required
def delete_org(org_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM organization WHERE org_id=%s", (org_id,))
    org = cur.fetchone()
    if org:
        cur.execute("DELETE FROM organization WHERE org_id=%s", (org_id,))
        mysql.connection.commit()
        flash(f"Organization '{org[0]}' deleted.", "success")
    else:
        flash("Organization not found.", "danger")
    cur.close()
    return redirect(url_for('admin.admin_dashboard') + '?tab=organizations')


# ─────────────────────────────────────────
# MANAGE ACTIVITIES  (kept for compatibility)
# ─────────────────────────────────────────
@admin_bp.route('/activities')
@admin_required
def manage_activities():
    cur = mysql.connection.cursor()
    cur.execute("SELECT activity_id, name, type, place, start_date, end_date, org_id FROM activity")
    activities = cur.fetchall()
    cur.close()
    return render_template('manage_activities.html', activities=activities)


# ─────────────────────────────────────────
# DELETE ACTIVITY
# ─────────────────────────────────────────
@admin_bp.route('/activity/delete/<int:activity_id>', methods=['POST'])
@admin_required
def delete_activity(activity_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM activity WHERE activity_id=%s", (activity_id,))
    act = cur.fetchone()
    if act:
        cur.execute("DELETE FROM activity WHERE activity_id=%s", (activity_id,))
        mysql.connection.commit()
        flash(f"Activity '{act[0]}' deleted.", "success")
    else:
        flash("Activity not found.", "danger")
    cur.close()
    return redirect(url_for('admin.admin_dashboard') + '?tab=activities')