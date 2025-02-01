from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3
import pandas as pd
import random
import datetime
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('assess.db')
    conn.row_factory = sqlite3.Row
    return conn

# Load the dataset
DATA_PATH = "adaptive_assessment_dataset.csv"
df = pd.read_csv(DATA_PATH)

# Function to get a random question based on difficulty level
def get_question(difficulty_level):
    questions = df[df["Difficulty Level"] == difficulty_level]
    if not questions.empty:
        return questions.sample(n=1).iloc[0]
    return None

# Function to adjust difficulty
def adjust_difficulty(is_correct, current_difficulty):
    if is_correct:
        return "Medium" if current_difficulty == "Easy" else "Hard" if current_difficulty == "Medium" else current_difficulty
    else:
        return "Medium" if current_difficulty == "Hard" else "Easy" if current_difficulty == "Medium" else current_difficulty

# Store response in database
def store_response(username, question_id, user_answer, correct_answer, is_correct, difficulty, topic):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO responses (username, question_id, user_answer, correct_answer, is_correct, difficulty, topic, timestamp)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (username, question_id, user_answer, correct_answer, is_correct, difficulty, topic, timestamp))
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials. Please try again.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return redirect(url_for('start_assessment'))

@app.route('/start_assessment', methods=['GET'])
def start_assessment():
    difficulty = "Easy"
    question = get_question(difficulty)
    if question is None:
        return jsonify({"error": "No questions found for this difficulty level."}), 404
    return render_template('question_page.html', question=question, difficulty=difficulty)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    # Step 1: Remove previous responses for the current session
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM responses WHERE username = ?', (username,))
    conn.commit()

    # Step 2: Collect data from the form and handle the current response
    data = request.form
    student_answer = data.get('answer').strip().lower()
    question_id = data.get('question_id')
    question = df[df["Question ID"] == question_id].iloc[0]
    correct_answer = question["Correct Answer"].strip().lower()
    is_correct = student_answer == correct_answer
    current_difficulty = question["Difficulty Level"]
    topic = question["Topic"]
    new_difficulty = adjust_difficulty(is_correct, current_difficulty)

    # Step 3: Store the current response in the database
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO responses (username, question_id, user_answer, correct_answer, is_correct, difficulty, topic, timestamp)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (username, question_id, student_answer, correct_answer, is_correct, current_difficulty, topic, timestamp))
    conn.commit()

    # Step 4: Get the next question based on the new difficulty
    next_question = get_question(new_difficulty)
    if next_question is None:
        return jsonify({"error": "No questions found for this difficulty level."}), 404

    return render_template('question_page.html', question=next_question, difficulty=new_difficulty, stop_test=True)

@app.route('/performance_report')
def performance_report():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    
    # Update the query to correctly fetch attempts and correct answers per topic
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT topic, difficulty, COUNT(*) AS attempts, SUM(is_correct) AS correct_count
        FROM responses
        WHERE username = ?
        GROUP BY topic, difficulty
        ORDER BY topic, difficulty
    ''', (username,))
    performance_data = cursor.fetchall()
    conn.close()

    # Prepare data for visualization and performance report
    topics = [row['topic'] for row in performance_data]
    difficulties = [row['difficulty'] for row in performance_data]
    attempts = [row['attempts'] for row in performance_data]
    correct_counts = [row['correct_count'] for row in performance_data]
    accuracies = [(c / a * 100 if a != 0 else 0) for c, a in zip(correct_counts, attempts)]  # Calculate accuracy

    # Plot accuracy by topic
    plt.figure(figsize=(8, 4))
    plt.bar(topics, accuracies, color='skyblue')
    plt.xlabel('Topic')
    plt.ylabel('Accuracy (%)')
    plt.title('Performance by Topic')
    plt.xticks(rotation=45)
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()

    # Prepare the report
    report_data = zip(topics, difficulties, attempts, correct_counts, accuracies)

    return render_template('report.html', report_data=report_data, chart_url=chart_url, stop_test=True)


@app.route('/stop_test')
def stop_test():
    return redirect(url_for('performance_report'))

if __name__ == '__main__':
    app.run(debug=True)
