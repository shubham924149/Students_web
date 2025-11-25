from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from functools import wraps

app = Flask(__name__)

# ---------------------- CONFIG ----------------------
app.secret_key = "change_this_secret_key"  # you can change this

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "rehankhan786"
DB_NAME = "myformdb"


def get_connection():
    """Creates and returns a new MySQL database connection."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ---------------------- LOGIN REQUIRED DECORATOR ----------------------
def login_required(f):
    """Decorator to protect routes that require login."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------- ROUTES ----------------------

@app.route("/")
def home():
    """Home page: if logged in go to dashboard, else login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------- Register ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Register route:
    - GET  : show register form
    - POST : create a new user
    """
    message = ""

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            message = "Username and password are required."
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()

                # check if user exists
                cur.execute("SELECT id FROM users WHERE username=%s", (username,))
                row = cur.fetchone()
                if row:
                    message = "Username already exists."
                else:
                    cur.execute(
                        "INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, password)
                    )
                    conn.commit()
                    message = "User registered successfully. You can login now."

                cur.close()
                conn.close()

            except mysql.connector.Error as err:
                message = f"Database Error: {err}"

    return render_template("register.html", message=message)


# ---------- Login ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route:
    - GET  : Displays login page
    - POST : Validates user credentials from MySQL database
    """
    message = ""

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username FROM users WHERE username=%s AND password=%s",
                (username, password)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                session["user_id"] = row[0]
                session["username"] = row[1]
                return redirect(url_for("dashboard"))
            else:
                message = "Incorrect username or password."
        except mysql.connector.Error as err:
            message = f"Database Error: {err}"

    return render_template("login.html", message=message)


# ---------- Logout ----------
@app.route("/logout")
@login_required
def logout():
    """Clear session and go back to login."""
    session.clear()
    return redirect(url_for("login"))


# ---------- Dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    """Simple dashboard page."""
    return render_template("dashboard.html")


# ---------- Students list (with optional search) ----------
@app.route("/students")
@login_required
def students():
    """
    Students page:
    - Fetches all students (or filtered) from the database
    - Sends them to the students.html template
    """
    students_list = []
    search_query = request.args.get("q", "").strip()

    try:
        conn = get_connection()
        cur = conn.cursor()

        if search_query:
            like = f"%{search_query}%"
            cur.execute(
                "SELECT id, name, email, age FROM students "
                "WHERE name LIKE %s OR email LIKE %s",
                (like, like)
            )
        else:
            cur.execute("SELECT id, name, email, age FROM students")

        rows = cur.fetchall()
        cur.close()
        conn.close()

        for row in rows:
            students_list.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "age": row[3],
            })

    except mysql.connector.Error as err:
        print("Database Error:", err)

    return render_template("students.html", students=students_list, q=search_query)


# ---------- Add Student ----------
@app.route("/add-student", methods=["GET", "POST"])
@login_required
def add_student():
    message = ""

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        age = request.form["age"].strip()

        if not name or not email or not age:
            message = "All fields are required."
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO students (name, email, age) VALUES (%s, %s, %s)",
                    (name, email, age)
                )
                conn.commit()
                cur.close()
                conn.close()

                return redirect(url_for("students"))

            except mysql.connector.Error as err:
                message = f"Database Error: {err}"

    return render_template("add_student.html", message=message)


# ---------- Edit Student ----------
@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    """
    Edit student:
    - GET  : show edit form with current student data
    - POST : update student in database
    """
    student_data = None
    message = ""

    if request.method == "POST":
        # Update student
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        age = request.form["age"].strip()

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE students SET name=%s, email=%s, age=%s WHERE id=%s",
                (name, email, age, student_id)
            )
            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for("students"))

        except mysql.connector.Error as err:
            message = f"Database Error: {err}"

    else:
        # GET – fetch current data
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name, email, age FROM students WHERE id=%s", (student_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                student_data = {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "age": row[3],
                }
            else:
                return "Student not found", 404

        except mysql.connector.Error as err:
            return f"Database Error: {err}", 500

    return render_template("edit_student.html", student=student_data, message=message)


# ---------- Delete Student ----------
@app.route("/delete-student/<int:student_id>")
@login_required
def delete_student(student_id):
    """
    Delete a student by ID, then redirect back to students list.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
        conn.commit()
        cur.close()
        conn.close()
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500

    return redirect(url_for("students"))


# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    app.run(debug=True)
