from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import psycopg2
import hashlib
import logging
import jwt
import requests
import json
import secrets
import string
import time
from dotenv import load_dotenv
from pathlib import Path
import traceback
import urllib.parse

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get('JWT_SECRET', 'barber-secret-key-2024')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7662525969:AAF33YcsBM8OmeURyarjx-bNxF9ghOVGRNc')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '531822805')

BASE_DIR = Path(__file__).parent.parent

app = Flask(__name__, 
           static_folder=str(BASE_DIR),
           static_url_path='',
           template_folder=str(BASE_DIR / 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
CORS(app)

def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        DATABASE_URL = 'postgresql://barber_db_33bs_user:BL1BlEQaugJijaXJC6VWOfpacuO6pAid@dpg-d63t4ih4tr6s73a46rtg-a.frankfurt-postgres.render.com/barber_db_33bs'
    return psycopg2.connect(DATABASE_URL)

def send_telegram_notification(appointment_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram токен или chat_id не указаны. Уведомление не отправлено.")
        return False
    
    try:
        message = f"📋 *НОВАЯ ЗАПИСЬ К БАРБЕРУ!*\n\n"
        message += f"👤 *Клиент:* {appointment_data['client_name']}\n"
        message += f"📞 *Телефон:* {appointment_data['client_phone']}\n"
        message += f"✂️ *Услуга:* {appointment_data['service_name']}\n"
        message += f"💰 *Цена:* {appointment_data['price']} руб.\n"
        message += f"📅 *Дата:* {appointment_data['date']}\n"
        message += f"⏰ *Время:* {appointment_data['time']}\n"
        message += f"👨‍💼 *Барбер:* {appointment_data.get('barber_name', appointment_data['barber_code'])}\n"
        message += f"🆔 *ID записи:* {appointment_data.get('appointment_id', 'новый')}\n"
        message += f"\n⏱ *Время записи:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Уведомление отправлено в Telegram")
            return True
        else:
            logger.error(f"❌ Ошибка отправки в Telegram: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке в Telegram: {e}")
        return False

def generate_random_password(length=6):
    characters = string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

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
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        barber_id INTEGER NOT NULL,
        name VARCHAR(100) NOT NULL,
        price INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE
    )
    ''')
    
    try:
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='services' AND column_name='active'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE services ADD COLUMN active BOOLEAN DEFAULT TRUE")
            logger.info("✅ Добавлена колонка 'active' в таблицу services")
    except Exception as e:
        logger.error(f"❌ Ошибка добавления колонки active: {e}")
    
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (barber_code) REFERENCES barbers(code) ON DELETE CASCADE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        username VARCHAR(100),
        photo_url TEXT,
        phone VARCHAR(20) UNIQUE,
        password_hash VARCHAR(255),
        last_barber_code VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS client_tokens (
        id SERIAL PRIMARY KEY,
        client_phone VARCHAR(20) NOT NULL,
        token VARCHAR(255) UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute("SELECT id FROM barbers WHERE code = 'barber'")
    if not cursor.fetchone():
        password_hash = hashlib.sha256('123456'.encode()).hexdigest()
        cursor.execute('''
        INSERT INTO barbers (name, code, password_hash, phone) 
        VALUES (%s, %s, %s, %s)
        RETURNING id
        ''', ('Тестовый Барбер', 'barber', password_hash, '+79990001122'))
        barber_result = cursor.fetchone()
        barber_id = barber_result[0] if barber_result else None
        logger.info("✅ Тестовый барбер создан")
    
    cursor.execute("SELECT id FROM services WHERE barber_id = (SELECT id FROM barbers WHERE code = 'barber')")
    if not cursor.fetchone():
        cursor.execute("SELECT id FROM barbers WHERE code = 'barber'")
        barber = cursor.fetchone()
        if barber:
            barber_id = barber[0]
            test_services = [
                (barber_id, 'Мужская стрижка', 1500, 45),
                (barber_id, 'Стрижка + Бритьё', 2000, 60),
                (barber_id, 'Королевское бритьё', 800, 30),
                (barber_id, 'Стрижка машинкой', 1000, 30),
                (barber_id, 'Оформление бороды', 600, 20),
                (barber_id, 'Детская стрижка', 1200, 40)
            ]
            for service in test_services:
                cursor.execute('''
                INSERT INTO services (barber_id, name, price, duration, active)
                VALUES (%s, %s, %s, %s, TRUE)
                ''', service)
            logger.info("✅ Тестовые услуги созданы")
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных PostgreSQL готова")

try:
    init_db()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации БД: {e}")

# ========== ФИКС ДЛЯ .HTML ФАЙЛОВ ==========
@app.route('/barber-login.html')
def redirect_barber_login_html():
    return redirect('/barber-login')

@app.route('/barber-panel.html')
def redirect_barber_panel_html():
    return redirect('/barber-panel')

@app.route('/client-login.html')
def redirect_client_login_html():
    return redirect('/client-login')

@app.route('/client-panel.html')
def redirect_client_panel_html():
    code = request.args.get('code', '')
    if code:
        return redirect(f'/client-panel?code={code}')
    return redirect('/client-panel')

@app.route('/client-profile.html')
def redirect_client_profile_html():
    return redirect('/client-profile')

@app.route('/profile.html')
def redirect_profile_html():
    return redirect('/profile')

# ========== СТАТИЧЕСКИЕ ФАЙЛЫ ==========
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'js'), filename)

@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'images'), filename)

# ========== ОСНОВНЫЕ СТРАНИЦЫ ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barber-login')
def barber_login_page():
    return render_template('barber-login.html')

@app.route('/barber-panel')
def barber_panel_page():
    # Проверяем токен из localStorage или URL
    token = request.args.get('token')
    if not token:
        # Пробуем получить из сессии или просто показываем страницу
        return render_template('barber-panel.html')
    
    # Если есть токен, проверяем его
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, code FROM barbers WHERE password_hash = %s', (token,))
        barber = cursor.fetchone()
        conn.close()
        
        if barber:
            # Сохраняем данные в сессии
            session['barber_id'] = barber[0]
            session['barber_name'] = barber[1]
            session['barber_code'] = barber[2]
            session['barber_token'] = token
            
    except Exception as e:
        logger.error(f"Ошибка проверки токена в barber-panel: {e}")
    
    return render_template('barber-panel.html')

@app.route('/client-login')
def client_login_page():
    error = request.args.get('error', '')
    code = request.args.get('code', '')
    return render_template('client-login.html', error=error, code=code)

@app.route('/client-panel')
def client_panel_page():
    try:
        return render_template('client-panel.html')
    except Exception as e:
        logger.error(f"Ошибка client-panel: {e}")
        return "Ошибка загрузки страницы", 500

@app.route('/client-profile')
def client_profile_page():
    return render_template('client-profile.html')

@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/master-login')
def master_login_page():
    return render_template('master-login.html')

@app.route('/master-panel')
def master_panel_page():
    return redirect('/barber-panel')

# ========== API ДЛЯ КЛИЕНТОВ ==========

@app.route('/api/client/register', methods=['POST'])
def client_register():
    try:
        data = request.json
        phone = data.get('phone', '').strip()
        send_to_telegram = data.get('send_to_telegram', True)
        telegram_data = data.get('telegram_data')
        
        if not phone:
            return jsonify({'success': False, 'error': 'Телефон не указан'}), 400
        
        # Проверяем валидность телефона
        if len(phone) < 10:
            return jsonify({'success': False, 'error': 'Некорректный номер телефона'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже клиент с таким телефоном
        cursor.execute('SELECT id FROM clients WHERE phone = %s', (phone,))
        existing_client = cursor.fetchone()
        
        if existing_client:
            # Клиент уже существует
            cursor.execute('SELECT password_hash FROM clients WHERE phone = %s', (phone,))
            client_data = cursor.fetchone()
            
            if client_data and client_data[0]:
                # Клиент уже зарегистрирован
                return jsonify({
                    'success': True,
                    'exists': True,
                    'phone': phone,
                    'password': 'уже установлен'
                })
        
        # Генерируем пароль
        password = generate_random_password()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Если есть Telegram данные - парсим их
        telegram_id = None
        first_name = ''
        last_name = ''
        username = ''
        photo_url = ''
        
        if telegram_data:
            try:
                params = dict(urllib.parse.parse_qsl(telegram_data))
                user_str = params.get('user')
                if user_str:
                    user_data = json.loads(user_str)
                    telegram_id = user_data.get('id')
                    first_name = user_data.get('first_name', '')
                    last_name = user_data.get('last_name', '')
                    username = user_data.get('username', '')
                    photo_url = user_data.get('photo_url', '')
            except Exception as e:
                logger.error(f"Ошибка парсинга Telegram данных: {e}")
        
        # Сохраняем клиента в БД
        cursor.execute('''
        INSERT INTO clients (phone, password_hash, telegram_id, first_name, last_name, username, photo_url, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (phone) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            telegram_id = COALESCE(EXCLUDED.telegram_id, clients.telegram_id),
            first_name = COALESCE(EXCLUDED.first_name, clients.first_name),
            last_name = COALESCE(EXCLUDED.last_name, clients.last_name),
            username = COALESCE(EXCLUDED.username, clients.username),
            photo_url = COALESCE(EXCLUDED.photo_url, clients.photo_url),
            updated_at = NOW()
        RETURNING id
        ''', (phone, password_hash, telegram_id, first_name, last_name, username, photo_url))
        
        client_id = cursor.fetchone()[0]
        
        # Генерируем токен для сессии
        token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(days=30)
        
        cursor.execute('''
        INSERT INTO client_tokens (client_phone, token, expires_at)
        VALUES (%s, %s, %s)
        ''', (phone, token, expires_at))
        
        conn.commit()
        
        # Отправляем пароль в Telegram если нужно
        if send_to_telegram and telegram_id and TELEGRAM_BOT_TOKEN:
            try:
                message = f"🎉 Добро пожаловать в iWant!\n\n"
                message += f"Ваш пароль для входа:\n"
                message += f"🔑 *{password}*\n\n"
                message += f"Телефон: {phone}\n\n"
                message += f"Используйте этот пароль для входа на сайте"
                
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                
                requests.post(url, json=payload, timeout=10)
                logger.info(f"✅ Пароль отправлен в Telegram для {phone}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки пароля в Telegram: {e}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'phone': phone,
            'password': password,
            'token': token,
            'client_id': client_id
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации клиента: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/client/auth', methods=['POST'])
def client_auth():
    try:
        data = request.json
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()
        
        if not phone or not password:
            return jsonify({'success': False, 'error': 'Телефон и пароль обязательны'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
        SELECT id, phone, first_name, last_name, telegram_id 
        FROM clients 
        WHERE phone = %s AND password_hash = %s
        ''', (phone, password_hash))
        
        client = cursor.fetchone()
        
        if not client:
            conn.close()
            return jsonify({'success': False, 'error': 'Неверный телефон или пароль'}), 401
        
        # Генерируем новый токен
        token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(days=30)
        
        # Удаляем старые токены
        cursor.execute('DELETE FROM client_tokens WHERE client_phone = %s', (phone,))
        
        # Сохраняем новый токен
        cursor.execute('''
        INSERT INTO client_tokens (client_phone, token, expires_at)
        VALUES (%s, %s, %s)
        ''', (phone, token, expires_at))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'token': token,
            'phone': phone,
            'client_id': client[0],
            'name': f"{client[2] or ''} {client[3] or ''}".strip() or 'Клиент'
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации клиента: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/client/session', methods=['GET'])
def client_session():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'authenticated': False}), 401
        
        token = auth_header.split(' ')[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем токен
        cursor.execute('''
        SELECT client_phone, expires_at 
        FROM client_tokens 
        WHERE token = %s AND expires_at > NOW()
        ''', (token,))
        
        token_data = cursor.fetchone()
        
        if not token_data:
            conn.close()
            return jsonify({'authenticated': False}), 401
        
        # Получаем данные клиента
        cursor.execute('''
        SELECT id, phone, first_name, last_name, telegram_id, created_at
        FROM clients 
        WHERE phone = %s
        ''', (token_data[0],))
        
        client = cursor.fetchone()
        conn.close()
        
        if client:
            return jsonify({
                'authenticated': True,
                'phone': client[1],
                'client_id': client[0],
                'name': f"{client[2] or ''} {client[3] or ''}".strip() or 'Клиент',
                'registration_date': client[5].strftime('%d.%m.%Y') if client[5] else None
            })
        
        return jsonify({'authenticated': False}), 401
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки сессии: {e}")
        return jsonify({'authenticated': False}), 401

@app.route('/api/client/check-phone', methods=['POST'])
def check_client_phone():
    try:
        data = request.json
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'exists': False}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password_hash FROM clients WHERE phone = %s', (phone,))
        client = cursor.fetchone()
        conn.close()
        
        if client and client[1]:  # Если есть password_hash
            return jsonify({'exists': True})
        else:
            return jsonify({'exists': False})
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки телефона: {e}")
        return jsonify({'exists': False}), 500

@app.route('/api/client/profile', methods=['GET'])
def get_client_profile():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401
        
        token = auth_header.split(' ')[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем токен
        cursor.execute('''
        SELECT client_phone 
        FROM client_tokens 
        WHERE token = %s AND expires_at > NOW()
        ''', (token,))
        
        token_data = cursor.fetchone()
        
        if not token_data:
            conn.close()
            return jsonify({'success': False, 'error': 'Невалидная сессия'}), 401
        
        # Получаем данные клиента
        cursor.execute('''
        SELECT id, phone, first_name, last_name, telegram_id, created_at
        FROM clients 
        WHERE phone = %s
        ''', (token_data[0],))
        
        client = cursor.fetchone()
        conn.close()
        
        if client:
            return jsonify({
                'success': True,
                'profile': {
                    'client_id': client[0],
                    'phone': client[1],
                    'first_name': client[2],
                    'last_name': client[3],
                    'telegram_id': client[4],
                    'registration_date': client[5].strftime('%d.%m.%Y') if client[5] else None
                }
            })
        
        return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения профиля: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка'}), 500

@app.route('/api/client/appointments', methods=['GET'])
def get_client_appointments():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401
        
        token = auth_header.split(' ')[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем токен и получаем телефон
        cursor.execute('''
        SELECT client_phone 
        FROM client_tokens 
        WHERE token = %s AND expires_at > NOW()
        ''', (token,))
        
        token_data = cursor.fetchone()
        
        if not token_data:
            conn.close()
            return jsonify({'success': False, 'error': 'Невалидная сессия'}), 401
        
        # Получаем записи клиента
        cursor.execute('''
        SELECT id, barber_code, client_name, client_phone, service_name, price, 
               appointment_date, appointment_time, status, created_at
        FROM appointments 
        WHERE client_phone = %s 
        ORDER BY appointment_date DESC, appointment_time DESC
        LIMIT 50
        ''', (token_data[0],))
        
        appointments = cursor.fetchall()
        
        result = []
        for app in appointments:
            result.append({
                'id': app[0],
                'barber_code': app[1],
                'client_name': app[2],
                'client_phone': app[3],
                'service_name': app[4],
                'price': app[5],
                'date': app[6].strftime('%d.%m.%Y'),
                'time': app[7].strftime('%H:%M'),
                'status': app[8],
                'created_at': app[9].strftime('%d.%m.%Y %H:%M')
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'appointments': result,
            'total': len(result)
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения записей: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка'}), 500

# ========== API ДЛЯ БАРБЕРОВ ==========

@app.route('/api/barber/check', methods=['GET'])
def check_barber_auth():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'authenticated': False, 'error': 'No token'}), 401
        
        token = auth_header.split(' ')[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем токен (в нашем случае токен = password_hash)
        cursor.execute('''
        SELECT id, name, code, phone 
        FROM barbers 
        WHERE password_hash = %s
        ''', (token,))
        
        barber = cursor.fetchone()
        conn.close()
        
        if barber:
            return jsonify({
                'authenticated': True,
                'barber': {
                    'id': barber[0],
                    'name': barber[1],
                    'code': barber[2],
                    'phone': barber[3]
                }
            })
        else:
            return jsonify({'authenticated': False, 'error': 'Invalid token'}), 401
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки барбера: {e}")
        return jsonify({'authenticated': False, 'error': 'Server error'}), 500

@app.route('/api/barber/login', methods=['POST'])
def barber_login():
    try:
        data = request.json
        barber_code = data.get('code', '').strip()
        password = data.get('password', '').strip()
        
        if not barber_code or not password:
            return jsonify({'success': False, 'error': 'Введите код и пароль'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
        SELECT id, name, code, phone 
        FROM barbers 
        WHERE code = %s AND password_hash = %s
        ''', (barber_code, password_hash))
        
        barber = cursor.fetchone()
        
        if not barber:
            conn.close()
            return jsonify({'success': False, 'error': 'Неверный код или пароль'}), 401
        
        conn.close()
        
        return jsonify({
            'success': True,
            'token': password_hash,
            'barber': {
                'id': barber[0],
                'name': barber[1],
                'code': barber[2],
                'phone': barber[3]
            },
            'redirect_url': f'/barber-panel?token={password_hash}'
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка входа барбера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/<barber_code>')
def get_barber(barber_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, code, phone FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        # Получаем услуги барбера
        cursor.execute('''
        SELECT id, name, price, duration, active 
        FROM services 
        WHERE barber_id = %s AND active = TRUE
        ORDER BY price
        ''', (barber[0],))
        
        services = cursor.fetchall()
        
        service_list = []
        for service in services:
            service_list.append({
                'id': service[0],
                'name': service[1],
                'price': service[2],
                'duration': service[3],
                'active': service[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'barber': {
                'id': barber[0],
                'name': barber[1],
                'code': barber[2],
                'phone': barber[3]
            },
            'services': service_list
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения данных барбера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/<barber_code>/booked-times')
def get_barber_booked_times(barber_code):
    try:
        date = request.args.get('date')
        if not date:
            return jsonify({'success': False, 'error': 'Дата не указана'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT appointment_time 
        FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s AND status = 'active'
        ''', (barber_code, date))
        
        booked_times = [row[0].strftime('%H:%M') for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'booked_times': booked_times
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения занятых времен: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/<barber_code>/services')
def get_barber_services(barber_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        cursor.execute('''
        SELECT id, name, price, duration, active 
        FROM services 
        WHERE barber_id = %s AND active = TRUE
        ORDER BY price
        ''', (barber[0],))
        
        services = cursor.fetchall()
        
        service_list = []
        for service in services:
            service_list.append({
                'id': service[0],
                'name': service[1],
                'price': service[2],
                'duration': service[3],
                'active': service[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'services': service_list
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения услуг барбера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/appointments', methods=['GET'])
def get_barber_appointments():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Не авторизован'}), 401
        
        token = auth_header.split(' ')[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем барбера по токену
        cursor.execute('SELECT id, code FROM barbers WHERE password_hash = %s', (token,))
        barber = cursor.fetchone()
        
        if not barber:
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 401
        
        # Получаем записи барбера
        cursor.execute('''
        SELECT id, barber_code, client_name, client_phone, service_name, price, 
               appointment_date, appointment_time, status, created_at
        FROM appointments 
        WHERE barber_code = %s 
        ORDER BY appointment_date DESC, appointment_time DESC
        LIMIT 50
        ''', (barber[1],))
        
        appointments = cursor.fetchall()
        
        result = []
        for app in appointments:
            result.append({
                'id': app[0],
                'barber_code': app[1],
                'client_name': app[2],
                'client_phone': app[3],
                'service_name': app[4],
                'price': app[5],
                'date': app[6].strftime('%d.%m.%Y'),
                'time': app[7].strftime('%H:%M'),
                'status': app[8],
                'created_at': app[9].strftime('%d.%m.%Y %H:%M')
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'appointments': result,
            'total': len(result)
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения записей барбера: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка'}), 500

# ========== API ДЛЯ ЗАПИСЕЙ ==========

@app.route('/api/appointments/create', methods=['POST'])
def create_appointment():
    try:
        data = request.json
        
        required_fields = ['barber_code', 'client_name', 'client_phone', 'service_name', 'date', 'time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Поле {field} обязательно'}), 400
        
        # Проверяем, что время свободно
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id 
        FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s AND appointment_time = %s AND status = 'active'
        ''', (data['barber_code'], data['date'], data['time']))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Это время уже занято'}), 400
        
        # Создаем запись
        cursor.execute('''
        INSERT INTO appointments (
            barber_code, client_name, client_phone, service_name, price,
            appointment_date, appointment_time, status, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', NOW())
        RETURNING id
        ''', (
            data['barber_code'],
            data['client_name'],
            data['client_phone'],
            data['service_name'],
            data.get('price', 0),
            data['date'],
            data['time']
        ))
        
        appointment_id = cursor.fetchone()[0]
        
        # Получаем имя барбера для уведомления
        cursor.execute('SELECT name FROM barbers WHERE code = %s', (data['barber_code'],))
        barber_result = cursor.fetchone()
        barber_name = barber_result[0] if barber_result else data['barber_code']
        
        conn.commit()
        
        # Отправляем уведомление в Telegram
        appointment_data = {
            'appointment_id': appointment_id,
            'barber_code': data['barber_code'],
            'barber_name': barber_name,
            'client_name': data['client_name'],
            'client_phone': data['client_phone'],
            'service_name': data['service_name'],
            'price': data.get('price', 0),
            'date': data['date'],
            'time': data['time']
        }
        
        send_telegram_notification(appointment_data)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'appointment_id': appointment_id,
            'message': 'Запись успешно создана'
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания записи: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== ДОПОЛНИТЕЛЬНЫЕ API ==========

@app.route('/api/client/find', methods=['GET', 'POST'])
def find_barber():
    try:
        if request.method == 'POST':
            code = request.form.get('code', '').strip()
        else:
            code = request.args.get('code', '').strip()
        
        logger.info(f"Поиск барбера по коду: {code}")
        
        if not code:
            logger.warning("Код барбера не указан")
            return redirect('/client-login')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            logger.info(f"Барбер найден: {result[1]} (код: {code})")
            return redirect(f'/client-panel?code={code}')
        else:
            logger.warning(f"Барбер не найден: {code}")
            return redirect(url_for('client_login_page', 
                                 error='Барбер с таким кодом не найден', 
                                 code=code))
    
    except Exception as e:
        logger.error(f"Ошибка в функции find_barber: {e}")
        return redirect(url_for('client_login_page', 
                             error='Ошибка сервера при поиске барбера'))

@app.route('/api/client/get-password', methods=['POST'])
def get_client_password():
    try:
        data = request.json
        phone = data.get('phone', '').strip()
        
        if not phone:
            return jsonify({'success': False, 'error': 'Телефон не указан'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем данные клиента
        cursor.execute('SELECT telegram_id FROM clients WHERE phone = %s', (phone,))
        client = cursor.fetchone()
        
        if not client or not client[0]:
            conn.close()
            return jsonify({'success': False, 'error': 'Клиент не найден или не привязан к Telegram'}), 404
        
        telegram_id = client[0]
        
        # Генерируем новый пароль
        new_password = generate_random_password()
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Обновляем пароль в БД
        cursor.execute('''
        UPDATE clients 
        SET password_hash = %s, updated_at = NOW() 
        WHERE phone = %s
        ''', (password_hash, phone))
        
        # Отправляем новый пароль в Telegram
        try:
            message = f"🔐 *Восстановление пароля iWant*\n\n"
            message += f"Ваш новый пароль:\n"
            message += f"🔑 *{new_password}*\n\n"
            message += f"Телефон: {phone}\n\n"
            message += f"Используйте этот пароль для входа на сайте"
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                conn.commit()
                conn.close()
                return jsonify({
                    'success': True,
                    'password': new_password,
                    'message': 'Новый пароль отправлен в Telegram'
                })
            else:
                conn.rollback()
                conn.close()
                return jsonify({'success': False, 'error': 'Ошибка отправки в Telegram'}), 500
                
        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"❌ Ошибка отправки пароля: {e}")
            return jsonify({'success': False, 'error': 'Ошибка отправки в Telegram'}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления пароля: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== API ДЛЯ УСЛУГ ==========

@app.route('/api/services', methods=['GET'])
def get_services():
    try:
        barber_code = request.args.get('barber_code')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if barber_code:
            cursor.execute('SELECT id FROM barbers WHERE code = %s', (barber_code,))
            barber = cursor.fetchone()
            
            if not barber:
                conn.close()
                return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
            
            cursor.execute('''
            SELECT s.id, s.name, s.price, s.duration, s.active, b.code as barber_code
            FROM services s
            JOIN barbers b ON s.barber_id = b.id
            WHERE s.barber_id = %s AND s.active = TRUE
            ORDER BY s.price
            ''', (barber[0],))
        else:
            cursor.execute('''
            SELECT s.id, s.name, s.price, s.duration, s.active, b.code as barber_code
            FROM services s
            JOIN barbers b ON s.barber_id = b.id
            WHERE s.active = TRUE
            ORDER BY b.code, s.price
            ''')
        
        services = cursor.fetchall()
        
        service_list = []
        for service in services:
            service_list.append({
                'id': service[0],
                'name': service[1],
                'price': service[2],
                'duration': service[3],
                'active': service[4],
                'barber_code': service[5]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'services': service_list
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения услуг: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
