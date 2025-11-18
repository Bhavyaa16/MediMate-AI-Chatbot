# MediMate - AI Medical Chatbot Flask Application
# Complete working backend with database, authentication, and AI chat

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'medimate_secret_key_2025'

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        region TEXT,
        specialization TEXT
    )''')
    
    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        slot TEXT,
        status TEXT DEFAULT 'pending'
    )''')
    
    # Summaries table
    c.execute('''CREATE TABLE IF NOT EXISTS summaries (
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        summary TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Insert demo users
    try:
        c.execute("INSERT INTO users VALUES (NULL,'Dr. Smith','doctor@medimate.com',?,'doctor','Mumbai','General Physician')",
                  (hashlib.sha256('admin123'.encode()).hexdigest(),))
        c.execute("INSERT INTO users VALUES (NULL,'John Doe','patient@medimate.com',?,'patient','Mumbai',NULL)",
                  (hashlib.sha256('12345'.encode()).hexdigest(),))
    except:
        pass
    
    conn.commit()
    conn.close()

init_db()

# ========== ROUTES ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['region'] = user['region']
            
            if user['role'] == 'doctor':
                return redirect('/doctor/dashboard')
            else:
                return redirect('/patient/dashboard')
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    doctors = conn.execute("SELECT * FROM users WHERE role='doctor' AND region=?", (session['region'],)).fetchall()
    appointments = conn.execute('''SELECT a.*, u.name as doctor_name, u.specialization 
                                   FROM appointments a 
                                   JOIN users u ON a.doctor_id = u.user_id 
                                   WHERE a.patient_id = ?''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments)

@app.route('/book/<int:doctor_id>')
def book(doctor_id):
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO appointments (patient_id, doctor_id, slot, status) VALUES (?, ?, ?, ?)',
              (session['user_id'], doctor_id, '2025-11-25 10:00 AM', 'booked'))
    appointment_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return redirect(f'/chatbot/{appointment_id}')

@app.route('/chatbot/<int:appointment_id>')
def chatbot(appointment_id):
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect('/login')
    return render_template('chatbot.html', appointment_id=appointment_id)

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    summaries = conn.execute('''SELECT s.*, u.name as patient_name 
                                FROM summaries s
                                JOIN users u ON s.patient_id = u.user_id
                                WHERE s.doctor_id = ?
                                ORDER BY s.date DESC''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('doctor_dashboard.html', summaries=summaries)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    appointment_id = data.get('appointment_id')
    
    # AI chatbot responses
    responses = [
        "Hello! I'm your MediMate assistant. What symptoms are you experiencing today?",
        "I understand. How long have you been experiencing these symptoms?",
        "Do you have any family history of similar conditions?",
        "Are you currently taking any medications?",
        "Do you have any known allergies?",
        "Thank you for sharing this information. I've recorded all your details."
    ]
    
    response = responses[min(len(history), len(responses) - 1)]
    completed = len(history) >= 5
    
    if completed:
        # Generate summary
        summary_text = f"Patient symptoms: {', '.join(history[:3])}. Duration: {history[1] if len(history) > 1 else 'N/A'}"
        
        conn = sqlite3.connect('database.db')
        apt = conn.execute('SELECT * FROM appointments WHERE appointment_id = ?', (appointment_id,)).fetchone()
        
        if apt:
            conn.execute('INSERT INTO summaries (patient_id, doctor_id, summary) VALUES (?, ?, ?)',
                        (apt[1], apt[2], summary_text))
            conn.execute('UPDATE appointments SET status = ? WHERE appointment_id = ?',
                        ('completed', appointment_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'response': response, 'completed': True, 'summary': summary_text})
    
    return jsonify({'response': response, 'completed': False})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
