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
        phone VARCHAR(20),
        last_barber_code VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    cursor.execute("SELECT id FROM clients WHERE telegram_id = %s", (1770537270377,))
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO clients (telegram_id, first_name, last_name, username)
        VALUES (%s, %s, %s, %s)
        ''', (
            1770537270377,
            'Реальный',
            'Пользователь',
            'real_user'
        ))
        logger.info("✅ Тестовый клиент создан")
    
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

@app.route("/barber-bookings")
def barber_bookings():
    return render_template("barber-bookings.html")

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

@app.route('/api/client/profile', methods=['GET'])
def get_client_profile():
    try:
        telegram_id = request.args.get('telegram_id')
        telegram_data = request.args.get('tg_data')
        
        logger.info(f"📱 Запрос профиля клиента. Telegram ID: {telegram_id}, Telegram Data: {'есть' if telegram_data else 'нет'}")
        
        final_telegram_id = None
        user_data_from_telegram = None
        
        if telegram_data:
            try:
                data_dict = {}
                for item in telegram_data.split('&'):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        data_dict[key] = value
                
                user_str = data_dict.get('user')
                if user_str:
                    user_data_from_telegram = json.loads(user_str)
                    telegram_id_from_data = user_data_from_telegram.get('id')
                    
                    if telegram_id_from_data:
                        final_telegram_id = int(telegram_id_from_data)
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (final_telegram_id,))
                        existing_user = cursor.fetchone()
                        
                        if existing_user:
                            cursor.execute('''
                            UPDATE clients SET 
                                first_name = %s,
                                last_name = %s,
                                username = %s,
                                photo_url = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE telegram_id = %s
                            ''', (
                                user_data_from_telegram.get('first_name', ''),
                                user_data_from_telegram.get('last_name', ''),
                                user_data_from_telegram.get('username', ''),
                                user_data_from_telegram.get('photo_url', ''),
                                final_telegram_id
                            ))
                        else:
                            cursor.execute('''
                            INSERT INTO clients (telegram_id, first_name, last_name, username, photo_url)
                            VALUES (%s, %s, %s, %s, %s)
                            ''', (
                                final_telegram_id,
                                user_data_from_telegram.get('first_name', ''),
                                user_data_from_telegram.get('last_name', ''),
                                user_data_from_telegram.get('username', ''),
                                user_data_from_telegram.get('photo_url', '')
                            ))
                        
                        conn.commit()
                        conn.close()
                        logger.info(f"✅ Профиль Telegram создан/обновлен: ID={final_telegram_id}")
                        
            except Exception as e:
                logger.error(f"❌ Ошибка обработки данных Telegram: {e}")
        
        if not final_telegram_id and telegram_id:
            try:
                if telegram_id.isdigit():
                    final_telegram_id = int(telegram_id)
                else:
                    logger.warning(f"⚠️ Telegram ID не является числом: {telegram_id}")
                    final_telegram_id = 1770537270377
            except ValueError:
                logger.error(f"❌ Не удалось преобразовать Telegram ID в число: {telegram_id}")
                final_telegram_id = 1770537270377
        
        if not final_telegram_id:
            final_telegram_id = 1770537270377
            logger.info(f"🧪 Используем тестовый Telegram ID: {final_telegram_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, telegram_id, first_name, last_name, username, 
               photo_url, phone, last_barber_code, created_at
        FROM clients 
        WHERE telegram_id = %s
        ''', (final_telegram_id,))
        
        result = cursor.fetchone()
        
        if result:
            profile = {
                'id': result[0],
                'telegram_id': result[1],
                'first_name': result[2] or 'Пользователь',
                'last_name': result[3] or '',
                'username': result[4] or '',
                'photo_url': result[5],
                'phone': result[6] or '',
                'last_barber_code': result[7],
                'created_at': result[8].isoformat() if result[8] else None
            }
            
            if user_data_from_telegram:
                profile.update({
                    'first_name': user_data_from_telegram.get('first_name', profile['first_name']),
                    'last_name': user_data_from_telegram.get('last_name', profile['last_name']),
                    'username': user_data_from_telegram.get('username', profile['username']),
                    'photo_url': user_data_from_telegram.get('photo_url', profile['photo_url'])
                })
            
            if profile.get('phone'):
                cursor.execute('''
                SELECT a.id, a.service_name, a.price, a.appointment_date, 
                       a.appointment_time, a.status, b.name as barber_name,
                       b.code as barber_code
                FROM appointments a
                LEFT JOIN barbers b ON a.barber_code = b.code
                WHERE a.client_phone = %s
                ORDER BY a.appointment_date DESC, a.appointment_time DESC
                LIMIT 10
                ''', (profile['phone'],))
                
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
                
                cursor.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM appointments 
                WHERE client_phone = %s
                ''', (profile['phone'],))
                
                stats = cursor.fetchone()
                
                stats_data = {
                    'total': stats[0] if stats else 0,
                    'completed': stats[1] if stats else 0
                }
            else:
                appointments = []
                stats_data = {'total': 0, 'completed': 0}
            
            conn.close()
            
            logger.info(f"✅ Профиль найден для telegram_id: {final_telegram_id}")
            
            return jsonify({
                'success': True,
                'profile': profile,
                'appointments': appointments,
                'stats': stats_data,
                'source': 'telegram' if telegram_data else 'local_storage'
            })
        else:
            conn.close()
            
            if user_data_from_telegram:
                profile = {
                    'telegram_id': final_telegram_id,
                    'first_name': user_data_from_telegram.get('first_name', 'Пользователь'),
                    'last_name': user_data_from_telegram.get('last_name', ''),
                    'username': user_data_from_telegram.get('username', ''),
                    'photo_url': user_data_from_telegram.get('photo_url', ''),
                    'phone': '',
                    'last_barber_code': None,
                    'created_at': datetime.now().isoformat()
                }
            else:
                profile = {
                    'telegram_id': final_telegram_id,
                    'first_name': 'Пользователь',
                    'last_name': '',
                    'username': '',
                    'photo_url': '',
                    'phone': '',
                    'last_barber_code': None,
                    'created_at': datetime.now().isoformat()
                }
            
            logger.info(f"🧪 Создан временный профиль для telegram_id: {final_telegram_id}")
            
            return jsonify({
                'success': True,
                'profile': profile,
                'appointments': [],
                'stats': {'total': 0, 'completed': 0},
                'temp_profile': True,
                'source': 'telegram_temp' if telegram_data else 'local_storage_temp'
            })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения профиля: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/profile/update', methods=['POST'])
def update_client_profile():
    try:
        data = request.json
        
        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return jsonify({'success': False, 'error': 'ID Telegram обязателен'}), 400
        
        try:
            telegram_id_int = int(telegram_id)
        except ValueError:
            return jsonify({'success': False, 'error': 'Неверный формат Telegram ID'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (telegram_id_int,))
        existing_user = cursor.fetchone()
        
        if existing_user:
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
                update_values.append(telegram_id_int)
                query = f"UPDATE clients SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = %s"
                cursor.execute(query, tuple(update_values))
        else:
            cursor.execute('''
            INSERT INTO clients (telegram_id, first_name, last_name, username, 
                               photo_url, phone, last_barber_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                telegram_id_int,
                data.get('first_name', ''),
                data.get('last_name', ''),
                data.get('username', ''),
                data.get('photo_url', ''),
                data.get('phone', ''),
                data.get('last_barber_code', '')
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Профиль клиента обновлен: {telegram_id_int}")
        
        return jsonify({
            'success': True,
            'message': 'Профиль сохранен'
        })
        
    except Exception as e:
        logger.error(f"Ошибка обновления профиля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== КЛИЕНТСКАЯ РЕГИСТРАЦИЯ ==========

def clean_phone_number(phone):
    """Очистка номера телефона"""
    if not phone:
        return ""
    digits = ''.join(filter(str.isdigit, phone))
    
    # Для узбекских номеров
    if digits.startswith('998'):
        return f"+{digits}"
    elif digits.startswith('7'):
        return f"+{digits}"
    else:
        return f"+998{digits[-9:]}"  # Берем последние 9 цифр

def generate_temp_password(length=6):
    """Генерация временного пароля"""
    alphabet = string.digits  # Только цифры для простоты
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_telegram_data(telegram_data, client_id):
    """Обновление данных Telegram для клиента"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        data_dict = {}
        for item in telegram_data.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                data_dict[key] = value
        
        user_str = data_dict.get('user')
        if user_str:
            user_data = json.loads(user_str)
            
            telegram_id = user_data.get('id')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            username = user_data.get('username', '')
            photo_url = user_data.get('photo_url', '')
            
            cursor.execute('''
            UPDATE clients SET 
                telegram_id = %s,
                first_name = %s,
                last_name = %s,
                username = %s,
                photo_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            ''', (telegram_id, first_name, last_name, username, photo_url, client_id))
            
            conn.commit()
            logger.info(f"✅ Данные Telegram обновлены для клиента {client_id}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления Telegram данных: {e}")

def send_telegram_credentials(telegram_data, phone, password):
    """Отправка логина и пароля в Telegram чат"""
    try:
        data_dict = {}
        for item in telegram_data.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                data_dict[key] = value
        
        user_str = data_dict.get('user')
        if user_str:
            user_data = json.loads(user_str)
            telegram_id = user_data.get('id')
            
            message = f"""
✅ Вы успешно зарегистрированы в iWant!

📱 Ваш логин: {phone}
🔑 Ваш пароль: {password}

💈 Теперь вы можете записываться к барберам!
🌐 Сайт: https://barber-booking-db.onrender.com
"""
            
            if TELEGRAM_BOT_TOKEN and telegram_id:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✅ Логин/пароль отправлены в Telegram: {telegram_id}")
                else:
                    logger.error(f"❌ Ошибка отправки в Telegram: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")

@app.route('/api/client/register', methods=['POST'])
def register_client():
    """Регистрация клиента"""
    try:
        data = request.json
        phone = data.get('phone')
        telegram_data = data.get('telegram_data')
        
        logger.info(f"📱 Регистрация клиента. Телефон: {phone}, Telegram данные: {'есть' if telegram_data else 'нет'}")
        
        if not phone:
            return jsonify({'success': False, 'error': 'Телефон обязателен'}), 400
        
        # Очищаем номер телефона
        phone = clean_phone_number(phone)
        
        # Генерируем пароль
        password = generate_temp_password()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже клиент
        cursor.execute('SELECT id, telegram_id FROM clients WHERE phone = %s', (phone,))
        existing_client = cursor.fetchone()
        
        if existing_client:
            client_id = existing_client[0]
            telegram_id = existing_client[1]
            
            # Если есть Telegram данные, обновляем
            if telegram_data:
                update_telegram_data(telegram_data, client_id)
            
            logger.info(f"✅ Клиент уже существует: ID={client_id}, телефон={phone}")
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Клиент уже зарегистрирован',
                'client_id': client_id,
                'telegram_id': telegram_id,
                'phone': phone,
                'password': password,
                'is_existing': True
            })
        
        # Создаем нового клиента
        cursor.execute('''
        INSERT INTO clients (phone, created_at, updated_at)
        VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id
        ''', (phone,))
        
        result = cursor.fetchone()
        new_client_id = result[0] if result else None
        
        if telegram_data:
            # Если есть данные Telegram, обновляем
            update_telegram_data(telegram_data, new_client_id)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Новый клиент зарегистрирован: ID={new_client_id}, телефон={phone}")
        
        # Отправляем данные в Telegram чат если есть telegram_data
        if telegram_data and data.get('send_to_telegram', True):
            send_telegram_credentials(telegram_data, phone, password)
        
        return jsonify({
            'success': True,
            'message': 'Регистрация успешна',
            'client_id': new_client_id,
            'phone': phone,
            'password': password,
            'is_existing': False
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации клиента: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/auth', methods=['POST'])
def client_auth():
    """Авторизация клиента"""
    try:
        data = request.json
        phone = data.get('phone')
        password = data.get('password')
        
        if not phone or not password:
            return jsonify({'success': False, 'error': 'Телефон и пароль обязательны'}), 400
        
        phone = clean_phone_number(phone)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Пока просто проверяем существование клиента
        cursor.execute('SELECT id FROM clients WHERE phone = %s', (phone,))
        client = cursor.fetchone()
        
        if client:
            # Генерируем токен для клиента
            token = jwt.encode({
                'client_id': client[0],
                'phone': phone,
                'exp': datetime.utcnow() + timedelta(days=30)
            }, JWT_SECRET, algorithm='HS256')
            
            conn.close()
            
            return jsonify({
                'success': True,
                'token': token,
                'client_id': client[0],
                'phone': phone
            })
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации клиента: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/session', methods=['GET'])
def check_client_session():
    """Проверка сессии клиента"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'authenticated': False})
        
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, phone FROM clients WHERE id = %s', (decoded['client_id'],))
        client = cursor.fetchone()
        conn.close()
        
        if client:
            return jsonify({
                'authenticated': True,
                'client': {
                    'id': client[0],
                    'phone': client[1]
                }
            })
        
        return jsonify({'authenticated': False})
        
    except:
        return jsonify({'authenticated': False})

# ========== КОНЕЦ КЛИЕНТСКОЙ РЕГИСТРАЦИИ ==========

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
               appointment_date, appointment_time, status, created_at
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
                'created_at': row[8].isoformat() if row[8] else None
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
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().date()
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s
        ''', (barber_code, today))
        today_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND status IN ('active', 'pending', 'confirmed')
        ''', (barber_code,))
        pending_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM appointments WHERE barber_code = %s
        ''', (barber_code,))
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE barber_code = %s AND status = 'completed'
        ''', (barber_code,))
        completed_count = cursor.fetchone()[0]
        
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
        
        cursor.execute('SELECT id FROM barbers WHERE code = %s', (code,))
        barber = cursor.fetchone()
        
        if not barber:
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        barber_id = barber[0]
        
        cursor.execute('''
        SELECT id, name, price, duration 
        FROM services 
        WHERE barber_id = %s
        ORDER BY price
        ''', (barber_id,))
        
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
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'success': False, 'error': 'Дата не указана'}), 400
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_hour = 10
        end_hour = 20
        slot_duration = 30
        
        cursor.execute('''
        SELECT appointment_time FROM appointments 
        WHERE barber_code = %s AND appointment_date = %s AND status != 'cancelled'
        ''', (code, date))
        
        booked_times = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        all_slots = []
        current_time = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
        
        while current_time < end_time:
            time_str = current_time.strftime('%H:%M')
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
                time_str = str(row[0])
                if ':' in time_str:
                    booked_times.append(time_str[:5])
        
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

@app.route('/api/appointments/create', methods=['POST'])
def create_client_appointment():
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
        
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            logger.error(f"❌ Барбер с кодом {barber_code} не найден в базе")
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        barber_name = barber[1] if barber[1] else f"Барбер {barber_code}"
        
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
            }), 409
        
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
            
            telegram_id = data.get('telegram_id')
            if telegram_id:
                cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (telegram_id,))
                existing_client = cursor.fetchone()
                
                if existing_client:
                    cursor.execute('''
                    UPDATE clients SET 
                        last_barber_code = %s,
                        phone = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = %s
                    ''', (barber_code, data['client_phone'], telegram_id))
                else:
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
                    'barber_code': barber_code,
                    'barber_name': barber_name
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

@app.route('/api/appointments/<int:appointment_id>/status', methods=['PUT'])
def update_appointment_status(appointment_id):
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
        UPDATE appointments SET status = %s
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

@app.route('/api/barber/register', methods=['POST'])
def register_barber():
    try:
        data = request.json
        
        required_fields = ['name', 'phone', 'code', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Поле {field} обязательно'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM barbers WHERE code = %s', (data['code'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Код уже используется другим барбером'}), 400
        
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        cursor.execute('''
        INSERT INTO barbers (name, phone, code, password_hash)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        ''', (data['name'], data['phone'], data['code'], password_hash))
        
        barber_id = cursor.fetchone()[0]
        
        basic_services = [
            (barber_id, 'Мужская стрижка', 1500, 45),
            (barber_id, 'Стрижка + Бритьё', 2000, 60),
            (barber_id, 'Королевское бритьё', 800, 30),
            (barber_id, 'Стрижка машинкой', 1000, 30),
            (barber_id, 'Оформление бороды', 600, 20),
            (barber_id, 'Детская стрижка', 1200, 40)
        ]
        
        for service in basic_services:
            cursor.execute('''
            INSERT INTO services (barber_id, name, price, duration, active)
            VALUES (%s, %s, %s, %s, TRUE)
            ''', service)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Новый барбер зарегистрирован: {data['name']} (код: {data['code']})")
        
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

@app.route('/api/telegram/auth', methods=['GET'])
def telegram_auth():
    try:
        telegram_data = request.args.get('tg_data')
        
        if telegram_data:
            logger.info(f"📱 Получены данные Telegram: {telegram_data[:100]}...")
            
            data_dict = {}
            for item in telegram_data.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    data_dict[key] = value
            
            user_str = data_dict.get('user')
            if user_str:
                try:
                    user_data = json.loads(user_str)
                    telegram_id = user_data.get('id')
                    first_name = user_data.get('first_name', 'Пользователь')
                    last_name = user_data.get('last_name', '')
                    username = user_data.get('username', '')
                    photo_url = user_data.get('photo_url')
                    
                    logger.info(f"📱 Данные пользователя Telegram: {first_name} {last_name} (@{username}), ID: {telegram_id}")
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT id FROM clients WHERE telegram_id = %s', (telegram_id,))
                    existing_user = cursor.fetchone()
                    
                    if existing_user:
                        cursor.execute('''
                        UPDATE clients SET 
                            first_name = %s,
                            last_name = %s,
                            username = %s,
                            photo_url = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE telegram_id = %s
                        RETURNING id
                        ''', (first_name, last_name, username, photo_url, telegram_id))
                    else:
                        cursor.execute('''
                        INSERT INTO clients (telegram_id, first_name, last_name, username, photo_url)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        ''', (telegram_id, first_name, last_name, username, photo_url))
                    
                    result = cursor.fetchone()
                    client_id = result[0] if result else None
                    
                    conn.commit()
                    conn.close()
                    
                    return jsonify({
                        'success': True,
                        'message': 'Данные Telegram сохранены',
                        'telegram_id': telegram_id
                    })
                    
                except Exception as e:
                    logger.error(f"Ошибка парсинга данных Telegram: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Telegram API работает'
        })
            
    except Exception as e:
        logger.error(f"Ошибка аутентификации через Telegram: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/all-appointments')
def debug_all_appointments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM appointments')
        total_count = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT id, barber_code, client_name, client_phone, service_name, 
               price, appointment_date, appointment_time, status, created_at
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
                'created_at': row[9].isoformat() if row[9] else None
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

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# ========== НОВЫЕ ФУНКЦИИ ДЛЯ СЕССИЙ И ПРОВЕРКИ ==========

@app.route('/api/client/check-phone', methods=['POST'])
def check_phone_exists():
    """Проверка существования номера телефона"""
    try:
        data = request.json
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'exists': False, 'error': 'Телефон не указан'}), 400
        
        # Очищаем номер
        phone = clean_phone_number(phone)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование клиента
        cursor.execute('SELECT id, phone FROM clients WHERE phone = %s', (phone,))
        existing_client = cursor.fetchone()
        
        conn.close()
        
        if existing_client:
            logger.info(f"📱 Клиент с телефоном {phone} уже существует")
            return jsonify({
                'exists': True,
                'message': 'Клиент уже зарегистрирован',
                'client_id': existing_client[0],
                'phone': existing_client[1]
            })
        else:
            logger.info(f"📱 Клиент с телефоном {phone} не найден - можно регистрировать")
            return jsonify({'exists': False, 'message': 'Клиент не найден'})
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки телефона: {e}")
        return jsonify({'exists': False, 'error': str(e)}), 500

@app.route('/api/client/check-session', methods=['GET'])
def check_client_session_status():
    """Проверка статуса сессии клиента"""
    try:
        # Проверяем токен из заголовка
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if token:
            try:
                decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                client_id = decoded.get('client_id')
                phone = decoded.get('phone')
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id, phone FROM clients WHERE id = %s', (client_id,))
                client = cursor.fetchone()
                conn.close()
                
                if client:
                    return jsonify({
                        'authenticated': True,
                        'client': {
                            'id': client[0],
                            'phone': client[1]
                        }
                    })
            except:
                pass
        
        # Проверяем телефон из localStorage
        phone = request.args.get('phone')
        if phone:
            phone = clean_phone_number(phone)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, phone FROM clients WHERE phone = %s', (phone,))
            client = cursor.fetchone()
            conn.close()
            
            if client:
                return jsonify({
                    'authenticated': True,
                    'client': {
                        'id': client[0],
                        'phone': client[1]
                    },
                    'has_password': True  # Предполагаем, что у клиента есть пароль
                })
        
        return jsonify({'authenticated': False, 'message': 'Сессия не найдена'})
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки сессии: {e}")
        return jsonify({'authenticated': False, 'error': str(e)}), 500

@app.route('/api/client/get-password', methods=['POST'])
def get_client_password():
    """Получение пароля клиента (для восстановления)"""
    try:
        data = request.json
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'success': False, 'error': 'Телефон обязателен'}), 400
        
        phone = clean_phone_number(phone)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM clients WHERE phone = %s', (phone,))
        client = cursor.fetchone()
        
        if client:
            # Генерируем новый пароль
            password = generate_temp_password()
            
            # Отправляем в Telegram если есть telegram_id
            cursor.execute('SELECT telegram_id FROM clients WHERE phone = %s', (phone,))
            telegram_result = cursor.fetchone()
            
            if telegram_result and telegram_result[0]:
                telegram_id = telegram_result[0]
                try:
                    message = f"""
🔑 Ваш пароль для входа в iWant:

📱 Логин: {phone}
🔑 Пароль: {password}

💈 Для входа используйте эти данные на сайте.
"""
                    
                    if TELEGRAM_BOT_TOKEN:
                        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        payload = {
                            'chat_id': telegram_id,
                            'text': message,
                            'parse_mode': 'Markdown'
                        }
                        
                        response = requests.post(url, json=payload, timeout=10)
                        if response.status_code == 200:
                            logger.info(f"✅ Пароль отправлен в Telegram: {telegram_id}")
                        else:
                            logger.error(f"❌ Ошибка отправки в Telegram: {response.text}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки пароля в Telegram: {e}")
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Пароль отправлен в Telegram',
                'phone': phone,
                'password': password
            })
        else:
            conn.close()
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения пароля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/logout', methods=['POST'])
def client_logout():
    """Выход клиента из системы"""
    try:
        data = request.json
        phone = data.get('phone')
        
        logger.info(f"👋 Выход клиента: {phone}")
        
        # В реальной системе здесь бы мы инвалидировали токен,
        # но для localStorage просто удаляем данные на клиенте
        
        return jsonify({
            'success': True,
            'message': 'Выход выполнен успешно'
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка выхода: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/dashboard', methods=['GET'])
def get_client_dashboard():
    """Главная страница клиента с барберами"""
    try:
        phone = request.args.get('phone')
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not phone and not token:
            return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401
        
        client_info = None
        
        # Если есть токен, проверяем его
        if token:
            try:
                decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                client_id = decoded.get('client_id')
                phone = decoded.get('phone')
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id, phone FROM clients WHERE id = %s', (client_id,))
                client = cursor.fetchone()
                conn.close()
                
                if client:
                    client_info = {'id': client[0], 'phone': client[1]}
            except:
                pass
        
        # Если нет токена, но есть телефон
        if not client_info and phone:
            phone = clean_phone_number(phone)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, phone FROM clients WHERE phone = %s', (phone,))
            client = cursor.fetchone()
            
            if client:
                client_info = {'id': client[0], 'phone': client[1]}
            
            conn.close()
        
        if not client_info:
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
        # Получаем барберов клиента (из истории записей)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT b.code, b.name, b.phone,
               COUNT(a.id) as total_appointments,
               MAX(a.appointment_date) as last_appointment
        FROM barbers b
        LEFT JOIN appointments a ON b.code = a.barber_code 
            AND a.client_phone = %s
        WHERE b.code IN (
            SELECT DISTINCT barber_code 
            FROM appointments 
            WHERE client_phone = %s
        )
        GROUP BY b.id, b.code, b.name, b.phone
        ORDER BY MAX(a.appointment_date) DESC
        ''', (client_info['phone'], client_info['phone']))
        
        barbers = []
        for row in cursor.fetchall():
            barbers.append({
                'code': row[0],
                'name': row[1] or f"Барбер {row[0]}",
                'phone': row[2],
                'total_appointments': row[3] or 0,
                'last_appointment': row[4].isoformat() if row[4] else None
            })
        
        # Получаем последние записи
        cursor.execute('''
        SELECT a.id, a.service_name, a.price, a.appointment_date, 
               a.appointment_time, a.status, b.name as barber_name,
               b.code as barber_code
        FROM appointments a
        LEFT JOIN barbers b ON a.barber_code = b.code
        WHERE a.client_phone = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 5
        ''', (client_info['phone'],))
        
        recent_appointments = []
        for row in cursor.fetchall():
            recent_appointments.append({
                'id': row[0],
                'service': row[1],
                'price': row[2],
                'date': row[3].isoformat() if row[3] else None,
                'time': str(row[4]) if row[4] else None,
                'status': row[5],
                'barber_name': row[6],
                'barber_code': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'client': client_info,
            'barbers': barbers,
            'recent_appointments': recent_appointments,
            'stats': {
                'total_barbers': len(barbers),
                'total_appointments': sum(b['total_appointments'] for b in barbers),
                'recent_appointments_count': len(recent_appointments)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения дашборда: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ДОПОЛНИТЕЛЬНЫЕ СТРАНИЦЫ ДЛЯ БАРБЕРА ==========
@app.route('/bookings')
def bookings_page():
    return render_template('bookings.html')

@app.route('/barber-finances')
def barber_finances_page():
    return render_template('barber-finances.html')

@app.route('/barber-profile')
def barber_profile_page():
    return render_template('barber-profile.html')

@app.route('/barber-schedule')
def barber_schedule_page():
    return render_template('barber-schedule.html')

@app.route('/barber-services')
def barber_services_page():
    return render_template('barber-services.html')

@app.route('/bookings.html')
def redirect_bookings_html():
    return redirect('/bookings')

@app.route('/barber-finances.html')
def redirect_barber_finances_html():
    return redirect('/barber-finances')

@app.route('/barber-profile.html')
def redirect_barber_profile_html():
    return redirect('/barber-profile')

@app.route('/barber-schedule.html')
def redirect_barber_schedule_html():
    return redirect('/barber-schedule')

@app.route('/barber-services.html')
def redirect_barber_services_html():
    return redirect('/barber-services')

# ========== ПЕРЕНАПРАВЛЕНИЯ ДЛЯ БАРБЕРА ==========
@app.route('/barber-profile')
def barber_profile_page_redirect():
    """Перенаправление на страницу профиля с проверкой авторизации"""
    token = request.args.get('token')
    
    if token:
        # Сохраняем токен из URL
        return render_template('barber-profile.html', token=token)
    
    # Проверяем авторизацию через заголовки
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            if decoded:
                return render_template('barber-profile.html')
        except:
            pass
    
    # Если не авторизован, перенаправляем на логин
    return redirect('/barber-login')

# Также добавьте проверку для barber-panel
@app.route('/barber-panel')
def barber_panel_page_redirect():
    """Перенаправление на панель с проверкой авторизации"""
    token = request.args.get('token')
    
    if token:
        return render_template('barber-panel.html', token=token)
    
    return render_template('barber-panel.html')

# ========== КОНЕЦ ДОПОЛНИТЕЛЬНЫХ СТРАНИЦ ==========

if __name__ == '__main__':
    print("=" * 80)
    # ... существующий код запуска ...

if __name__ == '__main__':
    print("=" * 80)
    print("🌐 BARBER BOOKING API ЗАПУЩЕН")
    print(f"🔑 JWT секрет: {JWT_SECRET[:10]}...")
    print(f"🤖 Telegram бот: {'активен' if TELEGRAM_BOT_TOKEN else 'не настроен'}")
    print("📌 Основные API маршруты:")
    print("   • POST /api/client/register - Регистрация клиента")
    print("   • POST /api/client/auth - Авторизация клиента")
    print("   • GET  /api/client/session - Проверка сессии клиента")
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
    print("   • GET  /api/telegram/auth - Аутентификация через Telegram")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
