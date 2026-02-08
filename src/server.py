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
    
    # Таблица услуг (добавляем barber_code вместо barber_id)
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
        print("✅ Тестовые услуги созданы")
    
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

@app.route('/client-panel')
def client_panel_page():
    # Получаем код барбера из параметра URL
    code = request.args.get('code', '')
    # Передаем код в шаблон для использования в JavaScript
    return render_template('client_panel.html', barber_code=code)

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

@app.route('/client-panel.html')
def redirect_client_panel():
    return redirect('/client-panel')

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
    return redirect(f'/client-panel?code={code}')

# ========== API ДЛЯ КЛИЕНТСКОГО ВХОДА ==========
@app.route('/api/client/login', methods=['POST'])
def client_login():
    """Авторизация клиента по коду барбера и редирект на client-panel"""
    try:
        data = request.json
        code = data.get('code')
        
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
                'redirect_url': f'/client-panel?code={code}'
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
    """Получение записей для барбера с улучшенным логированием"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    logger.info(f"Запрос на получение записей. Токен: {'представлен' if token else 'отсутствует'}")
    
    if not token:
        return jsonify({'error': 'Не авторизован'}), 401
    
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        barber_code = decoded['barber_code']
        logger.info(f"Барбер авторизован: {barber_code} (ID: {decoded['barber_id']}, имя: {decoded['barber_name']})")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Логируем запрос к базе
        logger.info(f"Выполняем запрос к БД для барбера: {barber_code}")
        
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
        
        logger.info(f"Найдено записей для барбера {barber_code}: {len(appointments)}")
        if len(appointments) > 0:
            for app in appointments[:3]:  # Показываем первые 3 записи в логах
                logger.info(f"  Запись: {app['client_name']} на {app['date']} {app['time']} ({app['service_name']})")
        
        return jsonify({'appointments': appointments})
        
    except jwt.ExpiredSignatureError:
        logger.error("Токен истек")
        return jsonify({'error': 'Токен истек', 'authenticated': False}), 401
    except jwt.InvalidTokenError:
        logger.error("Неверный токен")
        return jsonify({'error': 'Неверный токен', 'authenticated': False}), 401
    except Exception as e:
        logger.error(f"Ошибка при получении записей: {e}")
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

# ========== API ДЛЯ СОЗДАНИЯ ЗАПИСИ ==========
@app.route('/api/appointments/create', methods=['POST'])
def create_client_appointment():
    """Создание записи с улучшенным логированием"""
    try:
        data = request.json
        logger.info(f"Получен запрос на создание записи: {data}")
        
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
        logger.info(f"Создание записи для барбера: {barber_code}")
        
        # Проверяем существование барбера
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name FROM barbers WHERE code = %s', (barber_code,))
        barber = cursor.fetchone()
        
        if not barber:
            logger.error(f"Барбер с кодом {barber_code} не найден в базе")
            conn.close()
            return jsonify({'success': False, 'error': 'Барбер не найден'}), 404
        
        logger.info(f"Барбер найден: {barber[1]} (ID: {barber[0]})")
        
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
            
            # Получаем созданную запись для логирования
            cursor.execute('SELECT * FROM appointments WHERE id = %s', (appointment_id,))
            created_appointment = cursor.fetchone()
            
            logger.info(f"✅ Запись успешно создана! ID: {appointment_id}")
            logger.info(f"   Клиент: {data['client_name']}, тел: {data['client_phone']}")
            logger.info(f"   Услуга: {data['service_name']}, цена: {data['price']}")
            logger.info(f"   Дата: {data['date']}, время: {data['time']}")
            
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'Запись успешно создана',
                'appointment_id': appointment_id
            })
            
        except Exception as db_error:
            logger.error(f"Ошибка при вставке в БД: {db_error}")
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'error': f'Ошибка базы данных: {db_error}'}), 500
        
    except Exception as e:
        logger.error(f"Общая ошибка создания записи: {e}")
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

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
    print(f"📌 JWT секрет: {JWT_SECRET[:10]}...")
    print("📌 Доступные маршруты:")
    print("   • / - Главная страница")
    print("   • /barber-login - Вход барбера")
    print("   • /barber-panel - Панель барбера")
    print("   • /client-login - Вход клиента")
    print("   • /client-panel - Панель записи клиента")
    print("   • /api/barber/login - API вход барбера")
    print("   • /api/client/login - API вход клиента")
    print("   • /api/barber/<code>/services - Услуги барбера")
    print("   • /api/appointments/create - Создание записи")
    print("   • /api/debug/appointments - Отладка записей")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
