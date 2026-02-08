from flask import Flask, request, jsonify, send_from_directory, session, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import psycopg2
import hashlib
import logging
import jwt
import requests  # ДЛЯ TELEGRAM API
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
        # Используем твою внешнюю базу данных
        DATABASE_URL = 'postgresql://barber_db_33bs_user:BL1BlEQaugJijaXJC6VWOfpacuO6pAid@dpg-d63t4ih4tr6s73a46rtg-a.frankfurt-postgres.render.com/barber_db_33bs'
    return psycopg2.connect(DATABASE_URL)

# ========== ФУНКЦИЯ ОТПРАВКИ В TELEGRAM ==========
def send_telegram_notification(appointment_data):
    """Отправка уведомления админу в Telegram о новой записи"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram токен или chat_id не указаны. Уведомление не отправлено.")
        return False
    
    try:
        # Формируем красивое сообщение
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
        active BOOLEAN DEFAULT TRUE
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Создаем тестового барбера, если его нет
    cursor.execute("SELECT id FROM barbers WHERE code = 'barber'")
    if not cursor.fetchone():
        password_hash = hashlib.sha256('123456'.encode()).hexdigest()
        cursor.execute('''
        INSERT INTO barbers (name, code, password_hash) 
        VALUES (%s, %s, %s)
        ''', ('Тестовый Барбер', 'barber', password_hash))
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
    """Страница входа клиента с поиском барбера"""
    error = request.args.get('error', '')
    code = request.args.get('code', '')
    return render_template('client-login.html', error=error, code=code)

@app.route('/client-panel')
def client_panel_page():
    """Страница записи клиента - с проверкой существования барбера"""
    try:
        # Получаем код барбера из параметра URL
        code = request.args.get('code', '').strip()
        
        if not code:
            logger.warning("Код барбера не указан в URL при открытии client-panel")
            return redirect('/client-login')
        
        logger.info(f"Открытие client-panel для кода: {code}")
        
        # Проверяем существование барбера перед показом страницы
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (code,))
        barber = cursor.fetchone()
        conn.close()
        
        if not barber:
            logger.warning(f"Барбер не найден при открытии client-panel: {code}")
            return redirect(url_for('client_login_page', 
                                 error='Барбер с таким кодом не найден', 
                                 code=code))
        
        barber_name = barber[1] if barber[1] else f"Барбер {code}"
        logger.info(f"Барбер найден: {barber_name} (код: {code})")
        
        # ВАЖНОЕ ИСПРАВЛЕНИЕ: Исправляем имя файла шаблона
        return render_template('client-panel.html', 
                             barber_code=code, 
                             barber_name=barber_name)
        
    except Exception as e:
        logger.error(f"Ошибка в функции client_panel_page: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return redirect(url_for('client_login_page', 
                             error='Ошибка сервера при загрузке страницы'))

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

# ========== ПОИСК БАРБЕРА ==========
@app.route('/client/find', methods=['GET', 'POST'])
def find_barber():
    """Обработка поиска барбера - редирект на client-panel"""
    try:
        if request.method == 'POST':
            # Если POST запрос (из формы)
            code = request.form.get('code', '').strip()
        else:
            # Если GET запрос (из URL или кнопки)
            code = request.args.get('code', '').strip()
        
        logger.info(f"Поиск барбера по коду: {code}")
        
        if not code:
            logger.warning("Код барбера не указан")
            return redirect('/client-login')
        
        # Проверяем существование барбера
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

# ========== API ДЛЯ КЛИЕНТСКОГО ВХОДА ==========
@app.route('/api/client/login', methods=['POST'])
def client_login():
    """API авторизации клиента по коду барбера"""
    try:
        data = request.json
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'success': False, 'error': 'Введите код барбера'}), 400
        
        # Проверяем существование барбера с таким кодом
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, code FROM barbers WHERE code = %s', (code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Барбер найден - возвращаем URL для редиректа
            return jsonify({
                'success': True,
                'redirect_url': f'/client-panel?code={code}',
                'barber_name': result[1]
            })
        
        return jsonify({'success': False, 'error': 'Барбер с таким кодом не найден'}), 404
    
    except Exception as e:
        logger.error(f"Ошибка входа клиента: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

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
            # Создаем JWT токен
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
    """Получение записей для барбера - С ДИАГНОСТИКОЙ"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    logger.info(f"📥 ЗАПРОС ЗАПИСЕЙ. Токен: {'представлен' if token else 'отсутствует'}")
    
    # ДИАГНОСТИКА: логируем заголовки
    logger.info(f"📋 Заголовки запроса: {dict(request.headers)}")
    
    if not token:
        logger.error("❌ ТОКЕН ОТСУТСТВУЕТ! Барбер не авторизован.")
        return jsonify({'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        logger.info(f"✅ Барбер авторизован: {barber_code} (имя: {decoded['barber_name']})")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Логируем запрос к БД
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
        
        # ВАЖНАЯ ДИАГНОСТИКА
        logger.info(f"📊 Найдено записей для барбера {barber_code}: {len(appointments)}")
        
        if len(appointments) == 0:
            logger.warning(f"⚠️ ЗАПИСЕЙ НЕТ! Проверяем БД...")
            # Проверяем, есть ли вообще записи в базе
            conn2 = get_db_connection()
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT COUNT(*) FROM appointments WHERE barber_code = %s", (barber_code,))
            count_in_db = cursor2.fetchone()[0]
            conn2.close()
            logger.info(f"📈 Всего записей в БД для {barber_code}: {count_in_db}")
            
            # Проверяем все записи в БД
            conn3 = get_db_connection()
            cursor3 = conn3.cursor()
            cursor3.execute("SELECT barber_code, client_name, appointment_date FROM appointments LIMIT 10")
            all_records = cursor3.fetchall()
            conn3.close()
            logger.info(f"📝 Первые 10 записей в БД: {all_records}")
        
        return jsonify({'appointments': appointments})
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА ПРИ ПОЛУЧЕНИИ ЗАПИСЕЙ: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

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

# ========== API ДЛЯ УСЛУГ ==========
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
        
        # Если услуг нет, возвращаем демо-услуги
        if not services:
            services = [
                {'id': 1, 'name': 'Мужская стрижка', 'price': 1500, 'duration': 45},
                {'id': 2, 'name': 'Стрижка + Бритьё', 'price': 2000, 'duration': 60},
                {'id': 3, 'name': 'Королевское бритьё', 'price': 800, 'duration': 30}
            ]
        
        return jsonify(services)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки услуг: {e}")
        # Возвращаем демо-услуги при ошибке
        return jsonify([
            {'id': 1, 'name': 'Мужская стрижка', 'price': 1500, 'duration': 45},
            {'id': 2, 'name': 'Стрижка + Бритьё', 'price': 2000, 'duration': 60},
            {'id': 3, 'name': 'Королевское бритьё', 'price': 800, 'duration': 30}
        ])

# ========== API ДЛЯ СОЗДАНИЯ ЗАПИСИ (С УВЕДОМЛЕНИЕМ В TELEGRAM) ==========
@app.route('/api/appointments/create', methods=['POST'])
def create_client_appointment():
    """Создание записи с улучшенным логированием и уведомлением в Telegram"""
    try:
        data = request.json
        logger.info(f"📥 Получен запрос на создание записи: {data}")
        
        # Проверяем обязательные поля
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
        logger.info(f"✂️ Создание записи для барбера: {barber_code}")
        
        # Проверяем существование барбера
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            logger.error(f"❌ Барбер с кодом {barber_code} не найден в базе")
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        barber_name = barber[1] if barber[1] else f"Барбер {barber_code}"
        logger.info(f"✅ Барбер найден: {barber_name} (ID: {barber[0]})")
        
        # Создаем запись
        try:
            cursor.execute('''
            INSERT INTO appointments 
            (barber_code, client_name, client_phone, service_name, price, 
             appointment_date, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            ''', (
                barber_code,
                data['client_name'],
                data['client_phone'],
                data['service_name'],
                data['price'],
                data['date'],
                data['time']
            ))
            
            conn.commit()
            appointment_id = cursor.lastrowid
            
            logger.info(f"✅ Запись успешно создана! ID: {appointment_id}")
            logger.info(f"   👤 Клиент: {data['client_name']}, тел: {data['client_phone']}")
            logger.info(f"   ✂️ Услуга: {data['service_name']}, цена: {data['price']}")
            logger.info(f"   📅 Дата: {data['date']}, время: {data['time']}")
            
            # Подготавливаем данные для уведомления
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
            
            # Отправляем уведомление в Telegram (в фоновом режиме)
            try:
                send_telegram_notification(appointment_data)
            except Exception as tg_error:
                logger.warning(f"⚠️ Ошибка отправки в Telegram: {tg_error}")
            
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'Запись успешно создана',
                'appointment_id': appointment_id
            })
            
        except Exception as db_error:
            logger.error(f"❌ Ошибка при вставке в БД: {db_error}")
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'error': f'Ошибка базы данных: {db_error}'}), 500
        
    except Exception as e:
        logger.error(f"❌ Общая ошибка создания записи: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ========== ТЕСТОВЫЙ МАРШРУТ ДЛЯ ПРОВЕРКИ ==========
@app.route('/api/test/db-check')
def test_db_check():
    """Тестовый маршрут для проверки записей в БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем барберов
    cursor.execute("SELECT code, name FROM barbers")
    barbers = cursor.fetchall()
    
    # Проверяем все записи
    cursor.execute('''
    SELECT a.id, a.barber_code, b.name as barber_name, a.client_name, 
           a.appointment_date, a.appointment_time, a.created_at
    FROM appointments a
    LEFT JOIN barbers b ON a.barber_code = b.code
    ORDER BY a.created_at DESC
    LIMIT 20
    ''')
    appointments = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'barbers': barbers,
        'appointments': appointments,
        'total_barbers': len(barbers),
        'total_appointments': len(appointments)
    })

# ========== ДОПОЛНИТЕЛЬНЫЙ API ДЛЯ ДИАГНОСТИКИ ==========
@app.route('/api/debug/appointments', methods=['GET'])
def debug_appointments():
    """API для отладки - показывает все записи в базе"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT a.id, a.barber_code, b.name as barber_name, 
               a.client_name, a.client_phone, a.service_name, a.price,
               a.appointment_date, a.appointment_time, a.status, a.created_at
        FROM appointments a
        LEFT JOIN barbers b ON a.barber_code = b.code
        ORDER BY a.created_at DESC
        LIMIT 100
        ''')
        
        all_appointments = []
        for row in cursor.fetchall():
            all_appointments.append({
                'id': row[0],
                'barber_code': row[1],
                'barber_name': row[2],
                'client_name': row[3],
                'client_phone': row[4],
                'service_name': row[5],
                'price': row[6],
                'date': row[7].isoformat() if row[7] else None,
                'time': str(row[8]) if row[8] else None,
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            })
        
        conn.close()
        
        logger.info(f"Всего записей в базе: {len(all_appointments)}")
        
        # Группируем по барберам для статистики
        barber_stats = {}
        for app in all_appointments:
            barber_code = app['barber_code']
            if barber_code not in barber_stats:
                barber_stats[barber_code] = 0
            barber_stats[barber_code] += 1
        
        logger.info(f"Статистика по барберам: {barber_stats}")
        
        return jsonify({
            'total_appointments': len(all_appointments),
            'barber_stats': barber_stats,
            'appointments': all_appointments
        })
        
    except Exception as e:
        logger.error(f"Ошибка при отладке: {e}")
        return jsonify({'error': str(e)}), 500

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 80)
    print("🌐 BARBER BOOKING API ЗАПУЩЕН")
    print(f"🔑 JWT секрет: {JWT_SECRET[:10]}...")
    print(f"🤖 Telegram бот: {TELEGRAM_BOT_TOKEN[:10]}...")
    print("📌 Доступные маршруты:")
    print("   • / - Главная страница")
    print("   • /barber-login - Вход барбера")
    print("   • /barber-panel - Панель барбера (ДИАГНОСТИКА ВКЛЮЧЕНА)")
    print("   • /client-login - Вход клиента")
    print("   • /client-panel - Панель записи клиента (ИСПРАВЛЕНО)")
    print("   • /api/barber/login - API вход барбера")
    print("   • /api/barber/appointments - Записи барбера (С ЛОГАМИ)")
    print("   • /api/appointments/create - Создание записи (+Telegram)")
    print("   • /api/test/db-check - Проверка БД")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
