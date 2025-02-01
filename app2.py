from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
import random
import numpy as np
from scipy.optimize import minimize

app = Flask(__name__)  # Create the Flask app

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
df = pd.read_csv("TRAIN_ID.csv")

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

import sqlite3

def insert_response(user_id, question_id, is_correct):
    conn = sqlite3.connect('responses.db')
    cursor = conn.cursor()

    # Insert the response into the database
    cursor.execute(''' 
        INSERT INTO responses (userid, question_id, is_correct)
        VALUES (?, ?, ?)
    ''', (user_id, question_id, is_correct))

    conn.commit()
    conn.close()

@app.route("/submit_response", methods=["POST"])
@login_required
def submit_response():
    data = request.json
    user_answer = data.get("answer")
    correct_answer = data.get("correct_answer")
    question_id = data.get("question_id")  # Getting question_id from request data

    session["total_questions"] += 1  # Increment total questions attempted

    support_text = df[df["correct_answer"] == correct_answer]["support"].values[0]

    is_correct = 1 if user_answer == correct_answer else 0

    # Insert the response into the database
    insert_response(current_user.student_id, question_id, is_correct)

    if user_answer == correct_answer:
        session["score"] += 1  # Increment correct answers
        result = {"status": "correct", "message": "✅ Correct!", "support": ""}
    else:
        result = {"status": "incorrect", "message": f"❌ Incorrect! The correct answer is: {correct_answer}", "support": support_text}

    return jsonify(result)

def get_responses_from_db():
    conn = sqlite3.connect('responses.db')  # Update with your actual database path
    query = "SELECT userid, question_id, is_correct FROM responses"
    responses_df = pd.read_sql_query(query, conn)
    conn.close()
    return responses_df

# Define the difficulty calibration function
def calibrate_difficulty(responses_df):
    # Aggregate duplicate responses (taking the latest response or the mean if multiple responses exist)
    responses_df = responses_df.groupby(['userid', 'question_id'], as_index=False)['is_correct'].max()

    # Pivot the responses into a matrix
    response_matrix = responses_df.pivot(index='userid', columns='question_id', values='is_correct').fillna(0).values

    num_items = response_matrix.shape[1]
    num_users = response_matrix.shape[0]

    # Initial parameter guesses
    item_discrimination = np.ones(num_items)
    item_difficulty = np.zeros(num_items)
    user_ability = np.ones(num_users)

    # Logistic function for the 2PL model
    def logistic(theta, alpha, beta):
        return 1 / (1 + np.exp(-(alpha * (theta - beta))))

    # Negative log-likelihood function
    def nll(params, response_matrix, lambda_reg=0.1):
        item_discrimination = params[:num_items]
        item_difficulty = params[num_items:2*num_items]
        user_ability = params[2*num_items:]

        likelihood = 0
        for i in range(num_users):
            for j in range(num_items):
                p = logistic(user_ability[i], item_discrimination[j], item_difficulty[j])
                observed = response_matrix[i, j]
                likelihood += observed * np.log(p) + (1 - observed) * np.log(1 - p)

        # Add L2 regularization
        regularization = lambda_reg * (np.sum(item_discrimination**2) + np.sum(item_difficulty**2) + np.sum(user_ability**2))

        return -likelihood + regularization

    # Initial parameters
    params_initial = np.concatenate([item_discrimination, item_difficulty, user_ability])

    # Fit the IRT model
    result = minimize(nll, params_initial, args=(response_matrix,), method='BFGS')

    # Extract fitted parameters
    fitted_params = result.x
    fitted_item_discrimination = fitted_params[:num_items]
    fitted_item_difficulty = fitted_params[num_items:2*num_items]
    fitted_user_ability = fitted_params[2*num_items:]

    # Difficulty classification function
    def classify_difficulty(difficulty):
        if difficulty < -0.5:
            return "Very Easy"
        elif difficulty < 0:
            return "Easy"
        elif difficulty < 1:
            return "Medium"
        else:
            return "Hard"

    difficulty_labels = [classify_difficulty(d) for d in fitted_item_difficulty]

    # Load TRAIN_ID.csv file
    train_df = pd.read_csv('TRAIN_ID_with_difficulty.csv')

    # Assuming your dataset has a 'question_id' column, match difficulty to each question
    train_df['difficulty'] = train_df['question_id'].map(lambda x: difficulty_labels[x - 1] if x <= len(difficulty_labels) else "Unknown")

    return train_df

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
