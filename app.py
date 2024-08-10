from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from datetime import datetime, timezone
import random
import os
import csv

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Ensure the database file exists and create tables if necessary
def init_db():
    print("Initializing database...")
    if not os.path.exists('aria_arithmetic.db'):
        print("Creating new database and tables...")
        conn = sqlite3.connect('aria_arithmetic.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade FLOAT,
                time_spent FLOAT,
                timestamp TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                difficulty INTEGER NOT NULL,
                num_questions INTEGER NOT NULL,
                score INTEGER,
                time_spent FLOAT,
                timestamp TEXT,
                correct_answers INTEGER,
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        ''')
        conn.commit()
        conn.close()
        print("Database and tables created successfully.")
    else:
        print("Database already exists.")

# Helper function to generate a random math problem
def generate_problem(difficulty, operation):
    if operation == 'addition':
        num1 = random.randint(10**(difficulty-1), 10**difficulty - 1)
        num2 = random.randint(10**(difficulty-1), 10**difficulty - 1)
        question = f"{num1} + {num2}"
        answer = num1 + num2
    elif operation == 'multiplication':
        num1 = random.randint(1, 10**difficulty - 1)
        num2 = random.randint(1, 10**difficulty - 1)
        question = f"{num1} * {num2}"
        answer = num1 * num2
    return question, answer

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        username = request.form['username']
        age = request.form['age']
        operation = request.form['operation']
        difficulty = int(request.form['difficulty'])
        num_questions = int(request.form['num_questions'])

        # Initialize session variables for tracking the quiz
        session['username'] = username
        session['age'] = age
        session['operation'] = operation
        session['difficulty'] = difficulty
        session['num_questions'] = num_questions
        session['current_question'] = 0
        session['correct_answers'] = 0
        session['start_time'] = datetime.now(timezone.utc)

        return redirect(url_for('quiz_question'))
    
    return render_template('quiz.html')

@app.route('/quiz/question', methods=['GET', 'POST'])
def quiz_question():
    if request.method == 'POST':
        user_answer = int(request.form['answer'])
        correct_answer = session.get('correct_answer')

        # Track the current score
        if user_answer == correct_answer:
            session['correct_answers'] += 1

        # Save whether the answer was correct
        session['last_question_correct'] = (user_answer == correct_answer)

        # Move to the next question
        session['current_question'] += 1

        if session['current_question'] >= session['num_questions']:
            # Calculate time spent
            start_time = session.get('start_time')
            end_time = datetime.now(timezone.utc)
            time_spent = (end_time - start_time).total_seconds()

            # Save user and quiz result to the database
            conn = sqlite3.connect('aria_arithmetic.db')
            cursor = conn.cursor()

            # Check if user exists, if not insert new user
            cursor.execute('SELECT id FROM user WHERE username = ? AND age = ?', (session['username'], session['age']))
            user = cursor.fetchone()
            if not user:
                cursor.execute('''
                    INSERT INTO user (username, age, timestamp)
                    VALUES (?, ?, ?)
                ''', (session['username'], session['age'], datetime.now()))
                user_id = cursor.lastrowid
            else:
                user_id = user[0]

            # Calculate score as a percentage
            score_percentage = (session['correct_answers'] / session['num_questions']) * 100

            # Insert quiz result
            cursor.execute('''
                INSERT INTO quiz_result (user_id, operation, difficulty, num_questions, score, time_spent, timestamp, correct_answers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, session['operation'], session['difficulty'], session['num_questions'],
                  score_percentage, time_spent, datetime.now(), session['correct_answers']))
            
            conn.commit()
            conn.close()

            return redirect(url_for('results', user_id=user_id))
        else:
            # Generate the next question
            difficulty = session.get('difficulty')
            operation = session.get('operation')
            question, correct_answer = generate_problem(difficulty, operation)
            session['question'] = question
            session['correct_answer'] = correct_answer

            return render_template('quiz_question.html', question=question, last_correct=session.get('last_question_correct'))
    
    # Generate the first question
    difficulty = session.get('difficulty')
    operation = session.get('operation')
    question, correct_answer = generate_problem(difficulty, operation)
    session['question'] = question
    session['correct_answer'] = correct_answer

    return render_template('quiz_question.html', question=question, last_correct=None)

@app.route('/results/<int:user_id>')
def results(user_id):
    conn = sqlite3.connect('aria_arithmetic.db')
    cursor = conn.cursor()
    
    # Get user information
    cursor.execute('SELECT username, age FROM user WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    # Get the 10 most recent quiz results for this user
    cursor.execute('''
        SELECT operation, difficulty, num_questions, score, time_spent, timestamp, correct_answers 
        FROM quiz_result 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    ''', (user_id,))
    recent_scores = cursor.fetchall()
    
    conn.close()

    # Pass user_id correctly to the template
    return render_template('results.html', user=(user[0], user[1], user_id), recent_scores=recent_scores)

@app.route('/export/<int:user_id>')
def export_csv(user_id):
    conn = sqlite3.connect('aria_arithmetic.db')
    cursor = conn.cursor()
    
    # Get user information
    cursor.execute('SELECT username, age FROM user WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    # Get all quiz results for this user
    cursor.execute('''
        SELECT operation, difficulty, num_questions, score, time_spent, timestamp, correct_answers 
        FROM quiz_result 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    ''', (user_id,))
    results = cursor.fetchall()
    
    conn.close()

    # Create CSV file
    filename = f"{user[0]}_quiz_results.csv"
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Operation', 'Difficulty', 'Number of Questions', 'Score (%)', 'Time Spent (s)', 'Date', 'Correct Answers']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for result in results:
            writer.writerow({
                'Operation': result[0],
                'Difficulty': result[1],
                'Number of Questions': result[2],
                'Score (%)': result[3],
                'Time Spent (s)': result[4],
                'Date': result[5],
                'Correct Answers': result[6]
            })

    # Send the file to the user
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    init_db()  # Ensure the database is initialized
    app.run(debug=True)
