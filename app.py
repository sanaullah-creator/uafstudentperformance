from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import io
from openpyxl import Workbook
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key_here'

# ====================== MongoDB Connection ======================
client = MongoClient(app.config['MONGO_URI'])
db = client.get_default_database()

# Collections
users = db.users
students = db.students
subjects = db.subjects

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

        if users.find_one({"email": email}):
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)
        users.insert_one({
            "name": name,
            "email": email,
            "password": hashed
        })

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ====================== LOGIN ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        user = users.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')

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
    search = request.args.get('search', '').strip()

    query = {"user_id": session['user_id']}
    if search:
        query["$or"] = [
            {"student_name": {"$regex": search, "$options": "i"}},
            {"ag_number": {"$regex": search, "$options": "i"}}
        ]

    students_list = list(students.aggregate([
        {"$match": query},
        {"$lookup": {
            "from": "subjects",
            "localField": "_id",
            "foreignField": "student_id",
            "as": "subjects"
        }},
        {"$project": {
            "id": {"$toString": "$_id"},
            "student_name": 1,
            "ag_number": 1,
            "degree": 1,
            "section": 1,
            "shift": 1,
            "subject_count": {"$size": "$subjects"},
            "avg_percentage": {"$avg": "$subjects.percentage"},
            "gpa": {"$avg": "$subjects.grade_point"}
        }}
    ]))

    return render_template('dashboard.html', students=students_list, search=search)

# ====================== ALL STUDENTS ======================
@app.route('/all_students')
@login_required
def all_students():
    search = request.args.get('search', '').strip()
    query = {"user_id": session['user_id']}
    if search:
        query["$or"] = [
            {"student_name": {"$regex": search, "$options": "i"}},
            {"ag_number": {"$regex": search, "$options": "i"}}
        ]

    students_list = list(students.aggregate([
        {"$match": query},
        {"$lookup": {
            "from": "subjects",
            "localField": "_id",
            "foreignField": "student_id",
            "as": "subjects"
        }},
        {"$project": {
            "id": {"$toString": "$_id"},
            "student_name": 1,
            "ag_number": 1,
            "subject_count": {"$size": "$subjects"},
            "avg_percentage": {"$avg": "$subjects.percentage"},
            "gpa": {"$avg": "$subjects.grade_point"}
        }}
    ]))

    return render_template('all_students.html', students=students_list, search=search)

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

        # Insert Student
        student_doc = {
            "user_id": session['user_id'],
            "student_name": student_name,
            "ag_number": ag_number,
            "degree": degree,
            "section": section,
            "shift": shift
        }
        result = students.insert_one(student_doc)
        student_id = result.inserted_id

        # Insert Subjects
        i = 1
        while True:
            subject_name = request.form.get(f'subject_name_{i}')
            if not subject_name:
                break
            subject_name = subject_name.strip()
            if not subject_name:
                i += 1
                continue

            subject_id = request.form.get(f'subject_id_{i}', '').strip()
            credit_hours = int(request.form.get(f'credit_hours_{i}', 3))
            mid = float(request.form.get(f'mid_{i}', 0))
            sessional = float(request.form.get(f'sessional_{i}', 0))
            final = float(request.form.get(f'final_{i}', 0))
            total = float(request.form.get(f'total_{i}', 100))
            obtained = mid + sessional + final

            percentage = round((obtained / total) * 100, 2) if total > 0 else 0

            # Grading
            if percentage >= 85: grade, gp, status = "A", 4.00, "Excellent"
            elif percentage >= 80: grade, gp, status = "A-", 3.67, "Good"
            elif percentage >= 75: grade, gp, status = "B+", 3.33, "Good"
            elif percentage >= 70: grade, gp, status = "B", 3.00, "Good"
            elif percentage >= 65: grade, gp, status = "B-", 2.67, "Medium"
            elif percentage >= 61: grade, gp, status = "C+", 2.33, "Medium"
            elif percentage >= 58: grade, gp, status = "C", 2.00, "Medium"
            elif percentage >= 55: grade, gp, status = "C-", 1.67, "Medium"
            elif percentage >= 50: grade, gp, status = "D", 1.00, "Weak"
            else: grade, gp, status = "F", 0.00, "Weak"

            subjects.insert_one({
                "student_id": student_id,
                "subject_name": subject_name,
                "subject_id": subject_id,
                "credit_hours": credit_hours,
                "mid_marks": mid,
                "sessional_marks": sessional,
                "final_marks": final,
                "obtained_marks": obtained,
                "total_marks": total,
                "percentage": percentage,
                "grade": grade,
                "grade_point": gp,
                "status": status
            })
            i += 1

        flash(f'✅ {student_name} added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('prediction.html')

# ====================== STUDENT DETAIL ======================
@app.route('/student/<string:student_id>')
@login_required
def student_detail(student_id):
    student = students.find_one({"_id": ObjectId(student_id), "user_id": session['user_id']})
    if not student:
        flash('Student not found!', 'danger')
        return redirect(url_for('dashboard'))

    subjects_list = list(subjects.find({"student_id": ObjectId(student_id)}))

    return render_template('student_detail.html', student=student, subjects=subjects_list)

# ====================== EDIT STUDENT ======================
@app.route('/edit_student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if request.method == 'POST':
        student_name = request.form['student_name'].strip()
        ag_number = request.form['ag_number'].strip()

        students.update_one(
            {"_id": ObjectId(student_id), "user_id": session['user_id']},
            {"$set": {"student_name": student_name, "ag_number": ag_number}}
        )
        flash('Student updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    student = students.find_one({"_id": ObjectId(student_id), "user_id": session['user_id']})
    return render_template('edit_student.html', student=student)

# ====================== DELETE STUDENT ======================
@app.route('/delete_student/<string:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    subjects.delete_many({"student_id": ObjectId(student_id)})
    students.delete_one({"_id": ObjectId(student_id), "user_id": session['user_id']})
    flash('Record deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

# ====================== EXPORT EXCEL ======================
@app.route('/export_excel')
@login_required
def export_excel():
    records = list(students.aggregate([
        {"$match": {"user_id": session['user_id']}},
        {"$lookup": {
            "from": "subjects",
            "localField": "_id",
            "foreignField": "student_id",
            "as": "subjects"
        }},
        {"$unwind": "$subjects"}
    ]))

    wb = Workbook()
    ws = wb.active
    ws.title = "Performance Report"

    headers = ["Student Name", "AG Number", "Subject", "Subject ID", "Credit Hours",
               "Mid", "Sessional", "Final", "Obtained", "Total", "Percentage", "Grade", "GPA"]
    ws.append(headers)

    for rec in records:
        s = rec
        sub = rec['subjects']
        ws.append([
            s['student_name'], s['ag_number'], sub['subject_name'], sub.get('subject_id'),
            sub['credit_hours'], sub['mid_marks'], sub['sessional_marks'],
            sub['final_marks'], sub['obtained_marks'], sub['total_marks'],
            sub['percentage'], sub['grade'], sub['grade_point']
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"UAF_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

# ====================== MAIN ======================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8503)