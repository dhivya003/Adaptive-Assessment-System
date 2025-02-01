import sqlite3
def create_responses_db():
    conn = sqlite3.connect('responses.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT,
            question_id INTEGER,
            is_correct INTEGER,  -- 1 for correct, 0 for incorrect
            FOREIGN KEY(userid) REFERENCES students(userid)
        )
    ''')

    conn.commit()
    conn.close()

create_responses_db()
print("Database 'responses.db' and table 'responses' created successfully.")
