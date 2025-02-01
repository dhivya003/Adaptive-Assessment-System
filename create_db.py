import sqlite3

def create_database():
    conn = sqlite3.connect('adaptive.db')  # Create or connect to the database
    cursor = conn.cursor()

    # Create 'students' table to store user login credentials
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            userid TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

create_database()
print("Database 'adaptive.db' and table 'students' created successfully.")
