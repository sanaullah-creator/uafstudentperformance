from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import io
from openpyxl import Workbook
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# ====================== SECRET KEY ======================
app.secret_key = 'your_secret_key_here'


# ====================== DATABASE CONNECTION ======================
def get_db_connection():

    try:

        return mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB']
        )

    except Exception as e:

        print("Database Error:", e)

        return None


# ====================== LOGIN REQUIRED ======================
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'user_id' not in session:

            flash('Please login first.', 'danger')

            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return decorated_function


# ====================== HOME ======================
@app.route('/')
def home():

    return redirect(url_for('login'))


# ====================== REGISTER ======================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()

        if conn is None:

            flash('Database connection failed!', 'danger')

            return redirect(url_for('register'))

        cur = conn.cursor()

        try:

            cur.execute(
                "SELECT id FROM users WHERE email=%s",
                (email,)
            )

            if cur.fetchone():

                flash('Email already exists!', 'danger')

                cur.close()
                conn.close()

                return redirect(url_for('register'))

            hashed = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users
                (name, email, password)

                VALUES (%s, %s, %s)
            """, (
                name,
                email,
                hashed
            ))

            conn.commit()

            flash('Registration successful!', 'success')

            return redirect(url_for('login'))

        except Exception as e:

            conn.rollback()

            flash(f'Error: {str(e)}', 'danger')

        finally:

            cur.close()
            conn.close()

    return render_template('register.html')


# ====================== LOGIN ======================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()

        if conn is None:

            flash('Database connection failed!', 'danger')

            return redirect(url_for('login'))

        cur = conn.cursor()

        try:

            cur.execute(
                "SELECT * FROM users WHERE email=%s",
                (email,)
            )

            user = cur.fetchone()

            if user and check_password_hash(user[3], password):

                session['user_id'] = user[0]
                session['user_name'] = user[1]

                flash('Login successful!', 'success')

                return redirect(url_for('dashboard'))

            else:

                flash('Invalid credentials!', 'danger')

        except Exception as e:

            flash(f'Error: {str(e)}', 'danger')

        finally:

            cur.close()
            conn.close()

    return render_template('login.html')


# ====================== LOGOUT ======================
@app.route('/logout')
def logout():

    session.clear()

    flash('Logged out successfully.', 'info')

    return redirect(url_for('login'))


# ====================== DASHBOARD ======================
@app.route('/dashboard')
@login_required
def dashboard():

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('login'))

    cur = conn.cursor(dictionary=True)

    search = request.args.get('search', '').strip()

    query = """
        SELECT 
            s.id,
            s.student_name,
            s.ag_number,
            s.degree,
            s.section,
            s.shift,

            COUNT(sub.id) AS subject_count,

            ROUND(AVG(sub.percentage), 2) AS avg_percentage,

            ROUND(AVG(sub.grade_point), 2) AS gpa

        FROM students s

        LEFT JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s
    """

    params = [session['user_id']]

    if search:

        query += """
            AND (
                s.student_name LIKE %s
                OR s.ag_number LIKE %s
            )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    query += """
        GROUP BY s.id
        ORDER BY s.student_name
    """

    cur.execute(query, params)

    students = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        search=search
    )


# ====================== ALL STUDENTS ======================
@app.route('/all_students')
@login_required
def all_students():

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('dashboard'))

    cur = conn.cursor(dictionary=True)

    search = request.args.get('search', '').strip()

    query = """
        SELECT 
            s.id,
            s.student_name,
            s.ag_number,

            COUNT(sub.id) AS subject_count,

            ROUND(AVG(sub.percentage), 2) AS avg_percentage,

            ROUND(AVG(sub.grade_point), 2) AS gpa

        FROM students s

        LEFT JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s
    """

    params = [session['user_id']]

    if search:

        query += """
            AND (
                s.student_name LIKE %s
                OR s.ag_number LIKE %s
            )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    query += """
        GROUP BY s.id
        ORDER BY s.student_name
    """

    cur.execute(query, params)

    students = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'all_students.html',
        students=students,
        search=search
    )


# ====================== ADD STUDENT ======================
@app.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():

    if request.method == 'POST':

        student_name = request.form.get('student_name', '').strip()
        ag_number = request.form.get('ag_number', '').strip()
        degree = request.form.get('degree', '').strip()
        section = request.form.get('section', '').strip()
        shift = request.form.get('shift', '').strip()

        if not student_name or not ag_number:

            flash('Student name and AG number are required.', 'danger')

            return redirect(url_for('prediction'))

        conn = get_db_connection()

        if conn is None:

            flash('Database connection failed!', 'danger')

            return redirect(url_for('prediction'))

        cur = conn.cursor()

        try:

            # ================= INSERT STUDENT =================
            cur.execute("""
                INSERT INTO students
                (
                    user_id,
                    student_name,
                    ag_number,
                    degree,
                    section,
                    shift
                )

                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session['user_id'],
                student_name,
                ag_number,
                degree,
                section,
                shift
            ))

            student_id = cur.lastrowid

            # IMPORTANT FIX
            i = 1

            while True:

                subject_name = request.form.get(f'subject_name_{i}')

                if subject_name is None:
                    break

                subject_name = subject_name.strip()

                if not subject_name:
                    i += 1
                    continue

                subject_id = request.form.get(f'subject_id_{i}', '').strip()

                credit_hours = int(
                    request.form.get(f'credit_hours_{i}', 3)
                )

                mid = float(
                    request.form.get(f'mid_{i}', 0)
                )

                sessional = float(
                    request.form.get(f'sessional_{i}', 0)
                )

                final = float(
                    request.form.get(f'final_{i}', 0)
                )

                total = float(
                    request.form.get(f'total_{i}', 100)
                )

                obtained = mid + sessional + final

                if total > 0:
                    percentage = round((obtained / total) * 100, 2)
                else:
                    percentage = 0

                # ================= GRADING =================
                if percentage >= 85:
                    grade, gp, status = "A", 4.00, "Excellent"

                elif percentage >= 80:
                    grade, gp, status = "A-", 3.67, "Good"

                elif percentage >= 75:
                    grade, gp, status = "B+", 3.33, "Good"

                elif percentage >= 70:
                    grade, gp, status = "B", 3.00, "Good"

                elif percentage >= 65:
                    grade, gp, status = "B-", 2.67, "Medium"

                elif percentage >= 61:
                    grade, gp, status = "C+", 2.33, "Medium"

                elif percentage >= 58:
                    grade, gp, status = "C", 2.00, "Medium"

                elif percentage >= 55:
                    grade, gp, status = "C-", 1.67, "Medium"

                elif percentage >= 50:
                    grade, gp, status = "D", 1.00, "Weak"

                else:
                    grade, gp, status = "F", 0.00, "Weak"

                # ================= INSERT SUBJECT =================
                cur.execute("""
                    INSERT INTO subjects
                    (
                        student_id,
                        subject_name,
                        subject_id,
                        credit_hours,
                        mid_marks,
                        sessional_marks,
                        final_marks,
                        obtained_marks,
                        total_marks,
                        percentage,
                        grade,
                        grade_point,
                        status
                    )

                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                """, (
                    student_id,
                    subject_name,
                    subject_id,
                    credit_hours,
                    mid,
                    sessional,
                    final,
                    obtained,
                    total,
                    percentage,
                    grade,
                    gp,
                    status
                ))

                i += 1

            conn.commit()

            flash(
                f'✅ {student_name} added successfully!',
                'success'
            )

        except Exception as e:

            conn.rollback()

            flash(f'❌ Error: {str(e)}', 'danger')

        finally:

            cur.close()
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('prediction.html')


# ====================== STUDENT DETAIL ======================
@app.route('/student/<int:student_id>')
@login_required
def student_detail(student_id):

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('dashboard'))

    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT *
        FROM students
        WHERE id = %s
        AND user_id = %s
    """, (
        student_id,
        session['user_id']
    ))

    student = cur.fetchone()

    if not student:

        flash('Student not found!', 'danger')

        cur.close()
        conn.close()

        return redirect(url_for('dashboard'))

    cur.execute("""
        SELECT *
        FROM subjects
        WHERE student_id = %s
        ORDER BY subject_name
    """, (student_id,))

    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'student_detail.html',
        student=student,
        subjects=subjects
    )


# ====================== EDIT STUDENT ======================
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('dashboard'))

    cur = conn.cursor(dictionary=True)

    if request.method == 'POST':

        student_name = request.form['student_name'].strip()
        ag_number = request.form['ag_number'].strip()

        try:

            cur.execute("""
                UPDATE students
                SET student_name=%s,
                    ag_number=%s
                WHERE id=%s
                AND user_id=%s
            """, (
                student_name,
                ag_number,
                student_id,
                session['user_id']
            ))

            conn.commit()

            flash('Student updated successfully!', 'success')

            return redirect(url_for('dashboard'))

        except Exception as e:

            conn.rollback()

            flash(f'Error updating: {str(e)}', 'danger')

    cur.execute("""
        SELECT *
        FROM students
        WHERE id = %s
        AND user_id = %s
    """, (
        student_id,
        session['user_id']
    ))

    student = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('edit_student.html', student=student)


# ====================== DELETE STUDENT ======================
@app.route('/delete_student/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('dashboard'))

    cur = conn.cursor()

    try:

        cur.execute(
            "DELETE FROM subjects WHERE student_id=%s",
            (student_id,)
        )

        cur.execute("""
            DELETE FROM students
            WHERE id=%s
            AND user_id=%s
        """, (
            student_id,
            session['user_id']
        ))

        conn.commit()

        flash('Record deleted successfully.', 'success')

    except Exception as e:

        conn.rollback()

        flash(f'Error deleting record: {str(e)}', 'danger')

    finally:

        cur.close()
        conn.close()

    return redirect(url_for('dashboard'))


# ====================== EXPORT EXCEL ======================
@app.route('/export_excel')
@login_required
def export_excel():

    conn = get_db_connection()

    if conn is None:

        flash('Database connection failed!', 'danger')

        return redirect(url_for('dashboard'))

    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT
            s.student_name,
            s.ag_number,
            sub.subject_name,
            sub.subject_id,
            sub.credit_hours,
            sub.mid_marks,
            sub.sessional_marks,
            sub.final_marks,
            sub.obtained_marks,
            sub.total_marks,
            sub.percentage,
            sub.grade,
            sub.grade_point

        FROM students s

        JOIN subjects sub
        ON s.id = sub.student_id

        WHERE s.user_id = %s

        ORDER BY s.student_name
    """, (session['user_id'],))

    records = cur.fetchall()

    cur.close()
    conn.close()

    wb = Workbook()

    ws = wb.active

    ws.title = "Performance Report"

    headers = [
        "Student Name",
        "AG Number",
        "Subject",
        "Subject ID",
        "Credit Hours",
        "Mid",
        "Sessional",
        "Final",
        "Obtained",
        "Total",
        "Percentage",
        "Grade",
        "GPA"
    ]

    ws.append(headers)

    for row in records:
        ws.append(list(row.values()))

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    filename = f"UAF_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


# ====================== MAIN ======================
# ====================== MAIN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501)