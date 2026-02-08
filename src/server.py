from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import psycopg2
import hashlib
import logging
import jwt
import requests
from dotenv import load_dotenv
from pathlib import Path
import traceback

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# JWT секрет
JWT_SECRET = os.environ.get('JWT_SECRET', 'barber-secret-key-2024')

# Telegram Bot для уведомлений админу
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7662525969:AAF33YcsBM8OmeURyarjx-bNxF9ghOVGRNc')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '531822805')

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
    """Подключение к базе данных PostgreSQL на Render"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        DATABASE_URL = 'postgresql://barber_db_33bs_user:BL1BlEQaugJijaXJC6VWOfpacuO6pAid@dpg-d63t4ih4tr6s73a46rtg-a.frankfurt-postgres.render.com/barber_db_33bs'
    return psycopg2.connect(DATABASE_URL)

# ========== ФУНКЦИИ ОТПРАВКИ В TELEGRAM ==========
def send_telegram_notification(appointment_data):
    """Отправка уведомления админу в Telegram о новой записи"""
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

def send_barber_notification(barber_phone, appointment_data):
    """Отправка уведомления барберу"""
    logger.info(f"📱 Уведомление для барбера {barber_phone}: Новая запись от {appointment_data['client_name']}")
    return True

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ==========
def init_db():
    """Инициализация таблиц в базе данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица барберов
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
    
    # Таблица услуг
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        barber_code VARCHAR(20) NOT NULL,
        name VARCHAR(100) NOT NULL,
        price INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (barber_code) REFERENCES barbers(code) ON DELETE CASCADE
    )
    ''')
    
    # Таблица записей
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
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (barber_code) REFERENCES barbers(code) ON DELETE CASCADE
    )
    ''')
    
    # Таблица клиентов (для Telegram Mini App)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        username VARCHAR(100),
        photo_url TEXT,
        phone VARCHAR(20),
        last_barber_code VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица расписания
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schedule (
        id SERIAL PRIMARY KEY,
        barber_id INTEGER NOT NULL,
        date DATE NOT NULL,
        time TIME NOT NULL,
        is_available BOOLEAN DEFAULT TRUE,
        client_phone VARCHAR(20),
        FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE,
        UNIQUE(barber_id, date, time)
    )
    ''')
    
    # Создаем тестового барбера, если его нет
    cursor.execute("SELECT id FROM barbers WHERE code = 'barber'")
    if not cursor.fetchone():
        password_hash = hashlib.sha256('123456'.encode()).hexdigest()
        cursor.execute('''
        INSERT INTO barbers (name, code, password_hash, phone) 
        VALUES (%s, %s, %s, %s)
        ''', ('Тестовый Барбер', 'barber', password_hash, '+79990001122'))
        logger.info("✅ Тестовый барбер создан")
    
    # Создаем тестовые услуги для барбера
    cursor.execute("SELECT id FROM services WHERE barber_code = 'barber'")
    if not cursor.fetchone():
        test_services = [
            ('barber', 'Мужская стрижка', 1500, 45),
            ('barber', 'Стрижка + Бритьё', 2000, 60),
            ('barber', 'Королевское бритьё', 800, 30),
            ('barber', 'Стрижка машинкой', 1000, 30),
            ('barber', 'Оформление бороды', 600, 20),
            ('barber', 'Детская стрижка', 1200, 40)
        ]
        for service in test_services:
            cursor.execute('''
            INSERT INTO services (barber_code, name, price, duration)
            VALUES (%s, %s, %s, %s)
            ''', service)
        logger.info("✅ Тестовые услуги созданы")
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных PostgreSQL готова")

# Инициализация БД
try:
    init_db()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации БД: {e}")

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barber-login')
def barber_login_page():
    return render_template('barber-login.html')

@app.route('/barber-panel')
def barber_panel_page():
    return render_template('barber-panel.html')

@app.route('/client-login')
def client_login_page():
    error = request.args.get('error', '')
    code = request.args.get('code', '')
    return render_template('client-login.html', error=error, code=code)

@app.route('/client-panel')
def client_panel_page():
    try:
        code = request.args.get('code', '').strip()
        
        if not code:
            logger.warning("Код барбера не указан в URL при открытии client-panel")
            return redirect('/client-login')
        
        logger.info(f"Открытие client-panel для кода: {code}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, phone FROM barbers WHERE code = %s', (code,))
        barber = cursor.fetchone()
        conn.close()
        
        if not barber:
            logger.warning(f"Барбер не найден при открытии client-panel: {code}")
            return redirect(url_for('client_login_page', 
                                 error='Барбер с таким кодом не найден', 
                                 code=code))
        
        barber_name = barber[1] if barber[1] else f"Барбер {code}"
        barber_phone = barber[2] if barber[2] else 'Не указан'
        logger.info(f"Барбер найден: {barber_name} (код: {code})")
        
        return render_template('client-panel.html', 
                             barber_code=code, 
                             barber_name=barber_name,
                             barber_phone=barber_phone)
        
    except Exception as e:
        logger.error(f"Ошибка в функции client_panel_page: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('client_login_page', 
                             error='Ошибка сервера при загрузке страницы'))

@app.route('/client-profile')
def client_profile_page():
    """Страница профиля клиента"""
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

@app.route('/client/find', methods=['GET', 'POST'])
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

# ========== API ДЛЯ КЛИЕНТОВ ==========
@app.route('/api/client/login', methods=['POST'])
def client_login():
    try:
        data = request.json
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'success': False, 'error': 'Введите код барбера'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, code, phone FROM barbers WHERE code = %s', (code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'redirect_url': f'/client-panel?code={code}',
                'barber': {
                    'id': result[0],
                    'name': result[1],
                    'code': result[2],
                    'phone': result[3]
                }
            })
        
        return jsonify({'success': False, 'error': 'Барбер с таким кодом не найден'}), 404
    
    except Exception as e:
        logger.error(f"Ошибка входа клиента: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== API ДЛЯ КЛИЕНТСКОГО ПРОФИЛЯ ==========
@app.route('/api/client/profile', methods=['GET'])
def get_client_profile():
    """Получение профиля клиента"""
    try:
        # Получаем данные из Telegram или сессии
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'success': False, 'error': 'ID пользователя не указан'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли пользователь в базе
        cursor.execute('''
        SELECT id, telegram_id, first_name, last_name, username, 
               photo_url, phone, last_barber_code, created_at
        FROM clients 
        WHERE telegram_id = %s
        ''', (telegram_id,))
        
        result = cursor.fetchone()
        
        if result:
            # Пользователь найден
            profile = {
                'id': result[0],
                'telegram_id': result[1],
                'first_name': result[2],
                'last_name': result[3],
                'username': result[4],
                'photo_url': result[5],
                'phone': result[6],
                'last_barber_code': result[7],
                'created_at': result[8].isoformat() if result[8] else None
            }
            
            # Получаем историю записей
            cursor.execute('''
            SELECT a.id, a.service_name, a.price, a.appointment_date, 
                   a.appointment_time, a.status, b.name as barber_name,
                   b.code as barber_code
            FROM appointments a
            LEFT JOIN barbers b ON a.barber_code = b.code
            WHERE a.client_phone = %s OR a.client_name = %s
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
            LIMIT 10
            ''', (profile.get('phone', ''), f"{profile['first_name']} {profile['last_name']}"))
            
            appointments = []
            for row in cursor.fetchall():
                appointments.append({
                    'id': row[0],
                    'service': row[1],
                    'price': row[2],
                    'date': row[3].isoformat() if row[3] else None,
                    'time': str(row[4]) if row[4] else None,
                    'status': row[5],
                    'barber_name': row[6],
                    'barber_code': row[7]
                })
            
            # Получаем статистику
            cursor.execute('''
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM appointments 
            WHERE client_phone = %s OR client_name = %s
            ''', (profile.get('phone', ''), f"{profile['first_name']} {profile['last_name']}"))
            
            stats = cursor.fetchone()
            
            conn.close()
            
            return jsonify({
                'success': True,
                'profile': profile,
                'appointments': appointments,
                'stats': {
                    'total': stats[0] if stats else 0,
                    'completed': stats[1] if stats else 0
                }
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Профиль не найден',
                'needs_registration': True
            })
        
    except Exception as e:
        logger.error(f"Ошибка получения профиля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/profile/update', methods=['POST'])
def update_client_profile():
    """Обновление или создание профиля клиента"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return jsonify({'success': False, 'error': 'ID Telegram обязателен'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, есть ли пользователь
        cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (telegram_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Обновляем существующего пользователя
            update_fields = []
            update_values = []
            
            if 'first_name' in data:
                update_fields.append('first_name = %s')
                update_values.append(data['first_name'])
            
            if 'last_name' in data:
                update_fields.append('last_name = %s')
                update_values.append(data['last_name'])
            
            if 'username' in data:
                update_fields.append('username = %s')
                update_values.append(data['username'])
            
            if 'photo_url' in data:
                update_fields.append('photo_url = %s')
                update_values.append(data['photo_url'])
            
            if 'phone' in data:
                update_fields.append('phone = %s')
                update_values.append(data['phone'])
            
            if 'last_barber_code' in data:
                update_fields.append('last_barber_code = %s')
                update_values.append(data['last_barber_code'])
            
            if update_fields:
                update_values.append(telegram_id)
                query = f"UPDATE clients SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = %s"
                cursor.execute(query, tuple(update_values))
        else:
            # Создаем нового пользователя
            cursor.execute('''
            INSERT INTO clients (telegram_id, first_name, last_name, username, 
                               photo_url, phone, last_barber_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                telegram_id,
                data.get('first_name', ''),
                data.get('last_name', ''),
                data.get('username', ''),
                data.get('photo_url', ''),
                data.get('phone', ''),
                data.get('last_barber_code', '')
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Профиль клиента обновлен: {telegram_id}")
        
        return jsonify({
            'success': True,
            'message': 'Профиль сохранен'
        })
        
    except Exception as e:
        logger.error(f"Ошибка обновления профиля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        cursor.execute('SELECT id, name, code, phone FROM barbers WHERE code = %s AND password_hash = %s', (code, password_hash))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            token = jwt.encode({
                'barber_id': result[0],
                'barber_code': result[2],
                'barber_name': result[1],
                'barber_phone': result[3],
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, JWT_SECRET, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'token': token,
                'barber': {
                    'id': result[0],
                    'name': result[1],
                    'code': result[2],
                    'phone': result[3]
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
                'name': decoded['barber_name'],
                'phone': decoded.get('barber_phone', '')
            }
        })
    except:
        return jsonify({'authenticated': False})

@app.route('/api/barber/appointments', methods=['GET'])
def get_barber_appointments():
    """Получение записей для барбера"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    logger.info(f"📥 ЗАПРОС ЗАПИСЕЙ. Токен: {'представлен' if token else 'отсутствует'}")
    
    if not token:
        logger.error("❌ ТОКЕН ОТСУТСТВУЕТ! Барбер не авторизован.")
        return jsonify({'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        logger.info(f"✅ Барбер авторизован: {barber_code} (имя: {decoded['barber_name']})")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"🔍 Ищем записи для барбера: {barber_code}")
        
        cursor.execute('''
        SELECT id, client_name, client_phone, service_name, price,
               appointment_date, appointment_time, status, notes, created_at
        FROM appointments 
        WHERE barber_code = %s
        ORDER BY appointment_date DESC, appointment_time DESC
        LIMIT 50
        ''', (barber_code,))
        
        appointments = []
        rows = cursor.fetchall()
        logger.info(f"📊 Найдено строк в БД: {len(rows)}")
        
        for row in rows:
            appointments.append({
                'id': row[0],
                'client_name': row[1],
                'client_phone': row[2],
                'service_name': row[3],
                'price': row[4],
                'date': row[5].isoformat() if row[5] else None,
                'time': str(row[6]) if row[6] else None,
                'status': row[7],
                'notes': row[8],
                'created_at': row[9].isoformat() if row[9] else None
            })
        
        conn.close()
        
        logger.info(f"📦 Отправляем {len(appointments)} записей барберу")
        
        return jsonify({
            'success': True,
            'appointments': appointments,
            'count': len(appointments)
        })
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА ПРИ ПОЛУЧЕНИИ ЗАПИСЕЙ: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

@app.route('/api/barber/stats', methods=['GET'])
def get_barber_stats():
    """Получение статистики для барбера"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Сегодняшние записи
        today = datetime.now().date()
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s
        ''', (barber_code, today))
        today_count = cursor.fetchone()[0]
        
        # Ожидающие записи (active и pending)
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND status IN ('active', 'pending', 'confirmed')
        ''', (barber_code,))
        pending_count = cursor.fetchone()[0]
        
        # Всего записей
        cursor.execute('''
        SELECT COUNT(*) FROM appointments WHERE barber_code = %s
        ''', (barber_code,))
        total_count = cursor.fetchone()[0]
        
        # Выполненные записи
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND status = 'completed'
        ''', (barber_code,))
        completed_count = cursor.fetchone()[0]
        
        # Процент выполнения
        completion_rate = 0
        if total_count > 0:
            completion_rate = round((completed_count / total_count) * 100)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'today': today_count,
                'pending': pending_count,
                'total': total_count,
                'completed': completed_count,
                'completionRate': completion_rate
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    
    cursor.execute('SELECT id, name, code, phone FROM barbers WHERE code = %s', (code,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return jsonify({
            'success': True,
            'barber': {
                'id': result[0], 
                'name': result[1], 
                'code': result[2],
                'phone': result[3]
            }
        })
    
    return jsonify({'success': False, 'error': 'Барбер не найден'}), 404

@app.route('/api/barber/<code>/services', methods=['GET'])
def get_barber_services(code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, price, duration 
        FROM services 
        WHERE barber_code = %s AND active = TRUE
        ORDER BY price
        ''', (code,))
        
        services = []
        for row in cursor.fetchall():
            services.append({
                'id': row[0],
                'name': row[1],
                'price': row[2],
                'duration': row[3]
            })
        
        conn.close()
        
        if not services:
            # Возвращаем базовые услуги, если для барбера нет специфических
            services = [
                {'id': 1, 'name': 'Мужская стрижка', 'price': 1500, 'duration': 45},
                {'id': 2, 'name': 'Стрижка + Бритьё', 'price': 2000, 'duration': 60},
                {'id': 3, 'name': 'Королевское бритьё', 'price': 800, 'duration': 30}
            ]
        
        return jsonify({'success': True, 'services': services})
        
    except Exception as e:
        logger.error(f"Ошибка загрузки услуг: {e}")
        return jsonify({
            'success': False, 
            'services': [
                {'id': 1, 'name': 'Мужская стрижка', 'price': 1500, 'duration': 45},
                {'id': 2, 'name': 'Стрижка + Бритьё', 'price': 2000, 'duration': 60},
                {'id': 3, 'name': 'Королевское бритьё', 'price': 800, 'duration': 30}
            ]
        })

@app.route('/api/barber/<code>/available-slots', methods=['GET'])
def get_available_slots(code):
    """Получение доступных временных слотов для записи"""
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'success': False, 'error': 'Дата не указана'}), 400
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем рабочие часы барбера (можно добавить в таблицу barbers)
        # Пока используем стандартные часы: 10:00 - 20:00
        start_hour = 10
        end_hour = 20
        slot_duration = 30  # минут
        
        # Получаем занятые слоты на эту дату
        cursor.execute('''
        SELECT appointment_time FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s AND status != 'cancelled'
        ''', (code, date))
        
        booked_times = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Генерируем все возможные слоты
        all_slots = []
        current_time = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
        
        while current_time < end_time:
            time_str = current_time.strftime('%H:%M')
            # Проверяем, не занят ли слот
            is_booked = False
            for booked in booked_times:
                if str(booked) == time_str:
                    is_booked = True
                    break
            
            all_slots.append({
                'time': time_str,
                'available': not is_booked,
                'display': time_str
            })
            
            current_time += timedelta(minutes=slot_duration)
        
        return jsonify({
            'success': True,
            'date': date_str,
            'slots': all_slots
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения слотов: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barber/<code>/booked-times', methods=['GET'])
def get_barber_booked_times(code):
    """Получение занятых времен для конкретного барбера и даты"""
    try:
        date = request.args.get('date')
        
        if not date:
            return jsonify({'success': False, 'error': 'Не указана дата'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT appointment_time 
        FROM appointments 
        WHERE barber_code = %s 
          AND appointment_date = %s
          AND status != 'cancelled'
        ORDER BY appointment_time
        ''', (code, date))
        
        booked_times = []
        for row in cursor.fetchall():
            if row[0]:
                # Преобразуем время в строку HH:MM
                time_str = str(row[0])
                if ':' in time_str:
                    booked_times.append(time_str[:5])  # Берем только HH:MM
        
        conn.close()
        
        return jsonify({
            'success': True,
            'barber_code': code,
            'date': date,
            'booked_times': booked_times,
            'count': len(booked_times)
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения занятых времен: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ИСПРАВЛЕННЫЙ API ДЛЯ СОЗДАНИЯ ЗАПИСИ (с проверкой конфликта) ==========
@app.route('/api/appointments/create', methods=['POST'])
def create_client_appointment():
    """Создание записи - РАБОЧАЯ ВЕРСИЯ С ПРОВЕРКОЙ КОНФЛИКТА"""
    try:
        data = request.json
        logger.info(f"📥 Получен запрос на создание записи: {data}")
        
        required_fields = ['barber_code', 'client_name', 'client_phone', 'service_name', 'price', 'date', 'time']
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'
            logger.error(error_msg)
            return jsonify({'success': False, 'error': error_msg}), 400
        
        barber_code = data['barber_code']
        appointment_date = data['date']
        appointment_time = data['time']
        
        logger.info(f"✂️ Создание записи для барбера: {barber_code} на {appointment_date} в {appointment_time}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Проверяем существование барбера
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            logger.error(f"❌ Барбер с кодом {barber_code} не найден в базе")
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        barber_name = barber[1] if barber[1] else f"Барбер {barber_code}"
        
        # 2. ПРОВЕРЯЕМ КОНФЛИКТ ВРЕМЕНИ
        cursor.execute('''
        SELECT id, client_name, client_phone, service_name, appointment_time
        FROM appointments 
        WHERE barber_code = %s 
          AND appointment_date = %s 
          AND appointment_time = %s
          AND status != 'cancelled'
        ''', (barber_code, appointment_date, appointment_time))
        
        conflicting_appointment = cursor.fetchone()
        
        if conflicting_appointment:
            conn.close()
            logger.warning(f"⏰ Время уже занято! ID конфликтной записи: {conflicting_appointment[0]}")
            return jsonify({
                'success': False, 
                'error': 'Это время уже занято другим клиентом',
                'conflict_with': {
                    'id': conflicting_appointment[0],
                    'client_name': conflicting_appointment[1],
                    'client_phone': conflicting_appointment[2],
                    'service': conflicting_appointment[3],
                    'time': str(conflicting_appointment[4])
                }
            }), 409  # HTTP 409 Conflict
        
        # 3. Если время свободно - создаем запись
        try:
            cursor.execute('''
            INSERT INTO appointments 
            (barber_code, client_name, client_phone, service_name, price, 
             appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            RETURNING id
            ''', (
                barber_code,
                data['client_name'],
                data['client_phone'],
                data['service_name'],
                data['price'],
                appointment_date,
                appointment_time
            ))
            
            result = cursor.fetchone()
            appointment_id = result[0]
            
            # 4. СОХРАНЯЕМ/ОБНОВЛЯЕМ ПРОФИЛЬ КЛИЕНТА (если есть telegram_id)
            telegram_id = data.get('telegram_id')
            if telegram_id:
                # Проверяем, есть ли клиент
                cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (telegram_id,))
                existing_client = cursor.fetchone()
                
                if existing_client:
                    # Обновляем существующего клиента
                    cursor.execute('''
                    UPDATE clients SET 
                        last_barber_code = %s,
                        phone = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = %s
                    ''', (barber_code, data['client_phone'], telegram_id))
                else:
                    # Создаем нового клиента
                    cursor.execute('''
                    INSERT INTO clients (telegram_id, first_name, last_name, phone, last_barber_code)
                    VALUES (%s, %s, %s, %s, %s)
                    ''', (
                        telegram_id,
                        data.get('first_name', data['client_name'].split()[0] if data['client_name'] else ''),
                        data.get('last_name', ''),
                        data['client_phone'],
                        barber_code
                    ))
            
            conn.commit()
            
            logger.info(f"✅ Запись успешно создана! ID: {appointment_id}")
            
            appointment_data = {
                'appointment_id': appointment_id,
                'barber_code': barber_code,
                'barber_name': barber_name,
                'client_name': data['client_name'],
                'client_phone': data['client_phone'],
                'service_name': data['service_name'],
                'price': data['price'],
                'date': data['date'],
                'time': data['time']
            }
            
            try:
                send_telegram_notification(appointment_data)
            except Exception as tg_error:
                logger.warning(f"⚠️ Ошибка отправки в Telegram: {tg_error}")
            
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'Запись успешно создана',
                'appointment_id': appointment_id,
                'appointment': {
                    'id': appointment_id,
                    'client_name': data['client_name'],
                    'client_phone': data['client_phone'],
                    'service_name': data['service_name'],
                    'price': data['price'],
                    'date': data['date'],
                    'time': data['time'],
                    'barber_code': barber_code
                }
            })
            
        except Exception as db_error:
            logger.error(f"❌ Ошибка при вставке в БД: {db_error}")
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'error': f'Ошибка базы данных: {db_error}'}), 500
        
    except Exception as e:
        logger.error(f"❌ Общая ошибка создания записи: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== API ДЛЯ ОБНОВЛЕНИЯ СТАТУСА ЗАПИСИ ==========
@app.route('/api/appointments/<int:appointment_id>/status', methods=['PUT'])
def update_appointment_status(appointment_id):
    """Обновление статуса записи"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        
        data = request.json
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Не указан статус'}), 400
        
        valid_statuses = ['active', 'pending', 'confirmed', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'success': False, 'error': f'Недопустимый статус. Допустимые: {", ".join(valid_statuses)}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT barber_code FROM appointments WHERE id = %s', (appointment_id,))
        appointment = cursor.fetchone()
        
        if not appointment:
            conn.close()
            return jsonify({'success': False, 'error': 'Запись не найдена'}), 404
        
        if appointment[0] != barber_code:
            conn.close()
            return jsonify({'success': False, 'error': 'Нет прав для изменения этой записи'}), 403
        
        cursor.execute('''
        UPDATE appointments SET status = %s, 
        updated_at = CURRENT_TIMESTAMP 
        WHERE id = %s
        ''', (new_status, appointment_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Статус записи {appointment_id} обновлен на '{new_status}' для барбера {barber_code}")
        
        return jsonify({
            'success': True,
            'message': f'Статус обновлен на {new_status}',
            'appointment_id': appointment_id,
            'status': new_status
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== API ДЛЯ РЕГИСТРАЦИИ БАРБЕРОВ ==========
@app.route('/api/barber/register', methods=['POST'])
def register_barber():
    """Регистрация нового барбера"""
    try:
        data = request.json
        
        required_fields = ['name', 'phone', 'code', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Поле {field} обязательно'}), 400
        
        # Проверяем уникальность кода
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM barbers WHERE code = %s', (data['code'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Код уже используется другим барбером'}), 400
        
        # Хешируем пароль
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        # Создаем барбера
        cursor.execute('''
        INSERT INTO barbers (name, phone, code, password_hash)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        ''', (data['name'], data['phone'], data['code'], password_hash))
        
        barber_id = cursor.fetchone()[0]
        
        # Создаем базовые услуги для нового барбера
        basic_services = [
            (data['code'], 'Мужская стрижка', 1500, 45),
            (data['code'], 'Стрижка + Бритьё', 2000, 60),
            (data['code'], 'Королевское бритьё', 800, 30),
            (data['code'], 'Стрижка машинкой', 1000, 30),
            (data['code'], 'Оформление бороды', 600, 20),
            (data['code'], 'Детская стрижка', 1200, 40)
        ]
        
        for service in basic_services:
            cursor.execute('''
            INSERT INTO services (barber_code, name, price, duration)
            VALUES (%s, %s, %s, %s)
            ''', service)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Новый барбер зарегистрирован: {data['name']} (код: {data['code']})")
        
        # Автоматически логиним барбера
        token = jwt.encode({
            'barber_id': barber_id,
            'barber_code': data['code'],
            'barber_name': data['name'],
            'barber_phone': data['phone'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'Барбер успешно зарегистрирован',
            'token': token,
            'barber': {
                'id': barber_id,
                'name': data['name'],
                'code': data['code'],
                'phone': data['phone']
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка регистрации барбера: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ДИАГНОСТИЧЕСКИЕ МАРШРУТЫ ==========
@app.route('/api/debug/all-appointments')
def debug_all_appointments():
    """Получение ВСЕХ записей для проверки"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM appointments')
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT id, barber_code, client_name, client_phone, service_name, 
               price, appointment_date, appointment_time, status, notes, created_at
        FROM appointments 
        ORDER BY created_at DESC
        LIMIT 50
        ''')
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                'id': row[0],
                'barber_code': row[1],
                'client_name': row[2],
                'client_phone': row[3],
                'service_name': row[4],
                'price': row[5],
                'date': row[6].isoformat() if row[6] else None,
                'time': str(row[7]) if row[7] else None,
                'status': row[8],
                'notes': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            })
        
        conn.close()
        
        logger.info(f"📊 API /api/debug/all-appointments: всего записей в БД: {total_count}")
        
        return jsonify({
            'success': True,
            'appointments': appointments,
            'total': total_count
        })
        
    except Exception as e:
        logger.error(f"Ошибка в debug_all_appointments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test/create-appointment')
def test_create_appointment():
    """Тестовое создание записи напрямую в БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO appointments 
        (barber_code, client_name, client_phone, service_name, price, 
         appointment_date, appointment_time, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
        RETURNING id
        ''', (
            'barber',
            'Тестовый Клиент',
            '+79991234567',
            'Мужская стрижка',
            1500,
            datetime.now().date().isoformat(),
            '15:00'
        ))
        
        appointment_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Тестовая запись создана успешно! ID: {appointment_id}")
        
        return jsonify({
            'success': True,
            'message': f'Тестовая запись создана! ID: {appointment_id}',
            'id': appointment_id
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании тестовой записи: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test/db-structure')
def test_db_structure():
    """Проверка структуры БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        result = {'tables': []}
        
        for table_info in tables:
            table_name = table_info[0]
            
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
            except:
                count = -1
            
            cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position
            """, (table_name,))
            
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    'name': col[0],
                    'type': col[1]
                })
            
            result['tables'].append({
                'name': table_name,
                'row_count': count,
                'columns': columns
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'database_structure': result
        })
        
    except Exception as e:
        logger.error(f"Ошибка проверки структуры БД: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Проверка здоровья сервера"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 500

# ========== СТАТИЧЕСКИЕ ФАЙЛЫ ==========
@app.route('/<path:path>')
def serve_static(path):
    """Обслуживание статических файлов"""
    return send_from_directory(app.static_folder, path)

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 80)
    print("🌐 BARBER BOOKING API ЗАПУЩЕН")
    print(f"🔑 JWT секрет: {JWT_SECRET[:10]}...")
    print(f"🤖 Telegram бот: {'активен' if TELEGRAM_BOT_TOKEN else 'не настроен'}")
    print("📌 Основные API маршруты:")
    print("   • GET  /api/barber/appointments - Записи барбера")
    print("   • GET  /api/barber/stats - Статистика барбера")
    print("   • POST /api/barber/login - Вход барбера")
    print("   • POST /api/barber/register - Регистрация барбера")
    print("   • POST /api/appointments/create - Создание записи")
    print("   • PUT  /api/appointments/<id>/status - Обновление статуса")
    print("   • GET  /api/barber/<code>/services - Услуги барбера")
    print("   • GET  /api/barber/<code>/available-slots - Свободные слоты")
    print("   • GET  /api/barber/<code>/booked-times - Занятые времена")
    print("   • GET  /api/client/profile - Профиль клиента")
    print("   • POST /api/client/profile/update - Обновление профиля клиента")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
