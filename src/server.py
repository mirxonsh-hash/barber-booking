from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import psycopg2
import hashlib
import logging
import jwt
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# JWT секрет
JWT_SECRET = os.environ.get('JWT_SECRET', 'barber-secret-key-2024')

# Определяем корень проекта
BASE_DIR = Path(__file__).parent.parent

app = Flask(__name__, 
           static_folder=str(BASE_DIR),
           static_url_path='',
           template_folder=str(BASE_DIR / 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

# ========== ПОДКЛЮЧЕНИЕ К POSTGRESQL ==========
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не найден в переменных окружения")
    return psycopg2.connect(DATABASE_URL)

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ==========
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS barbers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        phone VARCHAR(20),
        code VARCHAR(20) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        work_days VARCHAR(50) DEFAULT '1,2,3,4,5,6',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        barber_code VARCHAR(20),
        client_name VARCHAR(100) NOT NULL,
        client_phone VARCHAR(20) NOT NULL,
        service_name VARCHAR(100),
        price INTEGER,
        appointment_date DATE NOT NULL,
        appointment_time TIME NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Создаем тестового барбера
    cursor.execute("SELECT id FROM barbers WHERE code = 'barber'")
    if not cursor.fetchone():
        password_hash = hashlib.sha256('123456'.encode()).hexdigest()
        cursor.execute('''
        INSERT INTO barbers (name, code, password_hash) 
        VALUES (%s, %s, %s)
        ''', ('Тестовый Барбер', 'barber', password_hash))
        print("✅ Тестовый барбер создан")
    
    conn.commit()
    conn.close()
    print("✅ База данных PostgreSQL готова")

try:
    init_db()
    print("✅ База данных инициализирована")
except Exception as e:
    print(f"❌ Ошибка инициализации БД: {e}")

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barber-login')
def barber_login_page():
    return render_template('barber-login.html')

@app.route('/barber-panel')
def barber_panel_page():
    # Проверяем токен из localStorage через параметр
    token = request.args.get('token', '')
    if not token:
        # Если нет токена, редирект на логин
        return redirect('/barber-login')
    
    try:
        # Проверяем токен
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # Если токен валидный, показываем панель
        return render_template('barber-panel.html')
    except:
        # Токен невалидный - на логин
        return redirect('/barber-login')

@app.route('/client-login')
def client_login_page():
    return render_template('client-login.html')

@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/master-login')
def master_login_page():
    return render_template('master-login.html')

@app.route('/master-panel')
def master_panel_page():
    # Редирект на barber-panel (убираем master-panel)
    return redirect('/barber-panel')

# ========== РЕДИРЕКТЫ ДЛЯ .HTML ==========
@app.route('/barber-login.html')
def redirect_barber_login():
    return redirect('/barber-login')

@app.route('/barber-panel.html')
def redirect_barber_panel():
    return redirect('/barber-panel')

@app.route('/client-login.html')
def redirect_client_login():
    return redirect('/client-login')

@app.route('/profile.html')
def redirect_profile():
    return redirect('/profile')

@app.route('/master-login.html')
def redirect_master_login():
    return redirect('/master-login')

@app.route('/master-panel.html')
def redirect_master_panel():
    return redirect('/barber-panel')

@app.route('/index.html')
def redirect_index():
    return redirect('/')

@app.route('/client-profile.html')
def redirect_client_profile():
    code = request.args.get('code', '')
    return redirect(f'/profile?code={code}')

# ========== API ДЛЯ БАРБЕРОВ ==========
@app.route('/api/barber/login', methods=['POST'])
def barber_login():
    try:
        data = request.json
        code = data.get('code')
        password = data.get('password')
        
        if not code or not password:
            return jsonify({'success': False, 'error': 'Требуется код и пароль'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, code FROM barbers WHERE code = %s AND password_hash = %s', (code, password_hash))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Создаем JWT токен (работает на Render)
            token = jwt.encode({
                'barber_id': result[0],
                'barber_code': result[2],
                'barber_name': result[1],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, JWT_SECRET, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'token': token,
                'barber': {
                    'id': result[0],
                    'name': result[1],
                    'code': result[2]
                }
            })
        
        return jsonify({'success': False, 'error': 'Неверный код или пароль'}), 401
    
    except Exception as e:
        logger.error(f"Ошибка входа: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/check', methods=['GET'])
def check_barber_auth():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'authenticated': False})
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return jsonify({
            'authenticated': True,
            'barber': {
                'id': decoded['barber_id'],
                'code': decoded['barber_code'],
                'name': decoded['barber_name']
            }
        })
    except:
        return jsonify({'authenticated': False})

@app.route('/api/barber/appointments', methods=['GET'])
def get_barber_appointments():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, client_name, client_phone, service_name, price,
               appointment_date, appointment_time, status, created_at
        FROM appointments 
        WHERE barber_code = %s
        ORDER BY appointment_date DESC, appointment_time DESC
        LIMIT 50
        ''', (barber_code,))
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                'id': row[0],
                'client_name': row[1],
                'client_phone': row[2],
                'service_name': row[3],
                'price': row[4],
                'date': row[5].isoformat() if row[5] else None,
                'time': str(row[6]) if row[6] else None,
                'status': row[7],
                'created_at': row[8].isoformat() if row[8] else None
            })
        
        conn.close()
        return jsonify({'appointments': appointments})
    except:
        return jsonify({'error': 'Не авторизован'}), 401

# ========== API ДЛЯ КЛИЕНТОВ ==========
@app.route('/api/barbers', methods=['GET'])
def get_all_barbers():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, code FROM barbers')
    barbers = [{'id': row[0], 'name': row[1], 'code': row[2]} for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(barbers)

@app.route('/api/barber/<code>', methods=['GET'])
def get_barber_by_code(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, code FROM barbers WHERE code = %s', (code,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return jsonify({
            'success': True,
            'barber': {'id': result[0], 'name': result[1], 'code': result[2]}
        })
    
    return jsonify({'success': False, 'error': 'Барбер не найден'}), 404

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 80)
    print("🌐 BARBER BOOKING API ЗАПУЩЕН")
    print(f"📌 JWT секрет: {JWT_SECRET[:10]}...")
    print("📌 Доступные маршруты:")
    print("   • /barber-login - Вход барбера")
    print("   • /barber-panel - Панель барбера")
    print("   • /api/barber/login - API вход (возвращает токен)")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
