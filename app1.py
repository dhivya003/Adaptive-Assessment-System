from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
import random

app = Flask(__name__)

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///adaptive.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
    print("✅ Database and tables created successfully!")

bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Student Model
class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return Student.query.get(int(user_id))

# Load questions from CSV
df = pd.read_csv("train.csv")

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student_id = request.form["student_id"]
        password = request.form["password"]
        student = Student.query.filter_by(student_id=student_id).first()

        if student and bcrypt.check_password_hash(student.password, password):
            login_user(student)
            session["score"] = 0  # Reset correct answers
            session["total_questions"] = 0  # Reset total questions
            return redirect(url_for("assessment"))
        else:
            return render_template("login2.html", error="Invalid Student ID or Password")

    return render_template("login2.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form["student_id"]
        password = request.form["password"]

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_student = Student(student_id=student_id, password=hashed_password)
        
        db.session.add(new_student)
        db.session.commit()
        
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/assessment")
@login_required
def assessment():
    return render_template("index2.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/get_question")
@login_required
def get_question():
    question = df.sample(1).to_dict(orient="records")[0]
    return jsonify(question)

@app.route("/submit_response", methods=["POST"])
@login_required
def submit_response():
    data = request.json
    user_answer = data.get("answer")
    correct_answer = data.get("correct_answer")

    session["total_questions"] += 1  # Increment total questions attempted

    support_text = df[df["correct_answer"] == correct_answer]["support"].values[0]

    if user_answer == correct_answer:
        session["score"] += 1  # Increment correct answers
        result = {"status": "correct", "message": "✅ Correct!", "support": ""}
    else:
        result = {"status": "incorrect", "message": f"❌ Incorrect! The correct answer is: {correct_answer}", "support": support_text}

    return jsonify(result)

@app.route('/stop_assessment', methods=['POST'])
@login_required
def stop_assessment():
    # Redirect to score page after finishing
    return redirect(url_for('score_page'))

@app.route('/score')
@login_required
def score_page():
    total_questions = session.get("total_questions", 0)  # Default to 0 if not found
    correct_answers = session.get("score", 0)
    incorrect_answers = total_questions - correct_answers  # Calculate incorrect answers

    return render_template('score.html', 
                           total_questions=total_questions, 
                           correct_answers=correct_answers, 
                           incorrect_answers=incorrect_answers)

if __name__ == "__main__":
    app.run(debug=True)