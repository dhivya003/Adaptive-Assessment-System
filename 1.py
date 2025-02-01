from flask import Flask, request, jsonify, render_template
import pandas as pd
import random

# Initialize Flask app
app = Flask(__name__)

# Load the dataset
# Replace 'studentAssessment.csv' with the path to your dataset.
student_assessments = pd.read_csv('studentAssessment.csv')
questions_difficulty = {
    "easy": ["What is 2 + 2?", "Name the capital of France."],
    "medium": ["Solve: 5x - 3 = 12.", "Explain the process of photosynthesis."],
    "hard": ["Write a program to implement Dijkstra's algorithm.", "Discuss quantum entanglement."]
}

# Home route - Render HTML template
@app.route('/')
def home():
    return render_template('home.html')

# Endpoint 1: Get a question calibrated to the student's performance
@app.route('/get_question', methods=['GET'])
def get_question():
    student_id = request.args.get('id_student', type=int)
    if student_id is None:
        return jsonify({"error": "Please provide a valid id_student parameter."}), 400

    student_data = student_assessments[student_assessments['id_student'] == student_id]
    if student_data.empty:
        question = random.choice(questions_difficulty["easy"])
        return jsonify({"student_id": student_id, "question": question, "difficulty": "easy"})

    avg_score = student_data['score'].mean()
    if avg_score < 50:
        question = random.choice(questions_difficulty["easy"])
        difficulty = "easy"
    elif 50 <= avg_score <= 80:
        question = random.choice(questions_difficulty["medium"])
        difficulty = "medium"
    else:
        question = random.choice(questions_difficulty["hard"])
        difficulty = "hard"

    return jsonify({"student_id": student_id, "question": question, "difficulty": difficulty})

# Endpoint 2: Submit a student's response
@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.get_json()
    if not data or "id_student" not in data or "question_id" not in data or "answer" not in data:
        return jsonify({"error": "Please provide id_student, question_id, and answer in the request body."}), 400

    response_analysis = {
        "correct": random.choice([True, False]),
        "feedback": "Good job!" if random.choice([True, False]) else "Try again with better focus."
    }
    return jsonify({"response_analysis": response_analysis})

# Endpoint 3: Generate a performance report for the student
@app.route('/get_report', methods=['GET'])
def get_report():
    student_id = request.args.get('id_student', type=int)
    if student_id is None:
        return jsonify({"error": "Please provide a valid id_student parameter."}), 400

    student_data = student_assessments[student_assessments['id_student'] == student_id]
    if student_data.empty:
        return jsonify({"error": "No performance data found for the given student ID."}), 404

    total_attempts = len(student_data)
    avg_score = student_data['score'].mean()
    performance_report = {
        "student_id": student_id,
        "total_attempts": total_attempts,
        "average_score": avg_score,
        "performance_category": "High" if avg_score > 80 else "Moderate" if avg_score >= 50 else "Low"
    }
    return jsonify({"performance_report": performance_report})

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)
