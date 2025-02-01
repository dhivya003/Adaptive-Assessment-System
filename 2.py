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

# Initialize the database
with app.app_context():
    db.create_all()

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
    question_data = {
        'question': question['question'],
        'correct_answer': question['correct_answer'],
        'distractor1': question['distractor1'],
        'distractor2': question['distractor2'],
        'distractor3': question['distractor3'],
        'support': question['support']
    }
    return jsonify(question_data)


@app.route("/submit_response", methods=["POST"])
@login_required
def submit_response():
    data = request.json
    user_answer = data.get("answer")
    correct_answer = data.get("correct_answer")

    support_text = df[df["correct_answer"] == correct_answer]["support"].values[0]

    if user_answer == correct_answer:
        result = {"status": "correct", "message": "✅ Correct!", "support": ""}
    else:
        result = {"status": "incorrect", "message": f"❌ Incorrect! The correct answer is: {correct_answer}", "support": support_text}

    return jsonify(result)
score = 85  # Example score, this should be dynamically calculated

@app.route('/stop_assessment', methods=['POST'])
def stop_assessment():
    # Process and calculate final score here (if needed)
    
    # Redirect to score page
    return redirect(url_for('score_page'))


@app.route('/score')
def score_page():
    # You can dynamically generate the score here based on the assessment data
    return render_template('score.html', score=score)


if __name__ == "__main__":
    app.run(debug=True)