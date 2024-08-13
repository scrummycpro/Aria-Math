from flask import Flask, render_template, request, redirect, url_for, make_response
import random
import nltk
from nltk.corpus import gutenberg
import sqlite3
import time
import csv
import io

app = Flask(__name__)

# Download NLTK data
nltk.download('gutenberg')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# Function to generate random sentences from Gutenberg corpus
def generate_random_sentences(num_sentences=10):
    sentences = nltk.sent_tokenize(gutenberg.raw())
    return random.sample(sentences, num_sentences)

# Function to extract parts of speech from a sentence
def extract_parts_of_speech(sentence):
    tokens = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(tokens)
    return tagged

# Function to select one random word for the quiz, excluding punctuation
def select_quiz_word(tagged_sentence):
    words_only = [(word, pos) for word, pos in tagged_sentence if word.isalpha()]
    if words_only:
        return random.choice(words_only)
    return None

# Database setup
def init_db():
    conn = sqlite3.connect('quiz.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (id INTEGER PRIMARY KEY, name TEXT, num_questions INTEGER, score REAL, timestamp TEXT, time_spent REAL)''')
    conn.commit()
    conn.close()

# Ensure the database is initialized when the app starts
init_db()

# Function to fetch the 10 most recent scores
def get_recent_scores():
    conn = sqlite3.connect('quiz.db')
    c = conn.cursor()
    c.execute("SELECT name, num_questions, score, timestamp, time_spent FROM results ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

# Route to explain parts of speech
@app.route('/')
def index():
    return render_template('index.html')

# Route to start the quiz
@app.route('/start', methods=['GET', 'POST'])
def start_quiz():
    if request.method == 'POST':
        name = request.form['name']
        num_questions = int(request.form['num_questions'])
        return redirect(url_for('quiz', name=name, num_questions=num_questions))
    return render_template('start.html')

# Route to display the quiz
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    name = request.args.get('name')
    num_questions = int(request.args.get('num_questions'))
    sentences = generate_random_sentences(num_questions)
    quiz_data = []

    for sentence in sentences:
        tagged_sentence = extract_parts_of_speech(sentence)
        quiz_word = select_quiz_word(tagged_sentence)
        if quiz_word:
            quiz_data.append((sentence, quiz_word))

    if request.method == 'POST':
        start_time = float(request.form['start_time'])
        end_time = time.time()
        time_spent = end_time - start_time

        correct_answers = 0
        results = []

        for i in range(num_questions):
            selected_pos = request.form[f'pos_{i}']
            correct_pos = request.form[f'correct_pos_{i}']
            word = request.form[f'word_{i}']

            if selected_pos == correct_pos:
                correct_answers += 1
                results.append((word, selected_pos, correct_pos, True))
            else:
                results.append((word, selected_pos, correct_pos, False))

        final_score = (correct_answers / num_questions) * 100

        conn = sqlite3.connect('quiz.db')
        c = conn.cursor()
        c.execute("INSERT INTO results (name, num_questions, score, timestamp, time_spent) VALUES (?, ?, ?, ?, ?)",
                  (name, num_questions, final_score, time.ctime(end_time), time_spent))
        conn.commit()
        conn.close()

        return render_template('quiz.html', quiz_data=quiz_data, results=results, final_score=final_score, show_results=True)

    start_time = time.time()
    return render_template('quiz.html', quiz_data=quiz_data, start_time=start_time, num_questions=num_questions, name=name, show_results=False)

# Route to display recent scores
@app.route('/recent-scores')
def recent_scores():
    scores = get_recent_scores()
    return render_template('recent_scores.html', scores=scores)

# Route to export recent scores to CSV
@app.route('/export-scores')
def export_scores():
    scores = get_recent_scores()

    # Create an in-memory CSV file
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Number of Questions', 'Score', 'Timestamp', 'Time Spent'])

    for row in scores:
        writer.writerow(row)

    output.seek(0)

    # Create a response object and set the appropriate headers
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=recent_scores.csv"
    response.headers["Content-type"] = "text/csv"

    return response

# Route to display the result
@app.route('/result')
def result():
    score = request.args.get('score')
    time_spent = request.args.get('time_spent')
    name = request.args.get('name')
    return render_template('result.html', score=score, time_spent=time_spent, name=name)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
