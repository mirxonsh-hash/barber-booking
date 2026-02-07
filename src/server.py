from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ========== НАСТРОЙКА ПУТЕЙ ДЛЯ ВАШЕЙ СТРУКТУРЫ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"📌 Текущая директория: {BASE_DIR}")
print(f"📌 Файлы в директории: {os.listdir('.')}")

# Проверяем существование папок
TEMPLATES_DIR = 'templates'
CSS_DIR = 'css'
JS_DIR = 'js'

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    # Барберы
    c.execute('''CREATE TABLE IF NOT EXISTS barbers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  phone TEXT,
                  code TEXT UNIQUE NOT NULL,
                  telegram_id TEXT UNIQUE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Услуги барберов
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  price INTEGER NOT NULL,
                  duration INTEGER NOT NULL,  # в минутах
                  FOREIGN KEY(barber_id) REFERENCES barbers(id) ON DELETE CASCADE)''')
    
    # Расписание (с 8:00 до 20:00, каждые 30 минут)
    c.execute('''CREATE TABLE IF NOT EXISTS schedule
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  service_id INTEGER,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,  # формат "HH:MM"
                  is_available BOOLEAN DEFAULT 1,
                  client_name TEXT,
                  client_phone TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id),
                  FOREIGN KEY(service_id) REFERENCES services(id))''')
    
    # Записи клиентов
    c.execute('''CREATE TABLE IF NOT EXISTS appointments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  service_id INTEGER NOT NULL,
                  client_name TEXT NOT NULL,
                  client_phone TEXT NOT NULL,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,
                  status TEXT DEFAULT 'pending',  # pending, confirmed, completed, cancelled
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id),
                  FOREIGN KEY(service_id) REFERENCES services(id))''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def create_test_data():
    """Создаем тестовые данные для демонстрации"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    try:
        # Очищаем старые данные
        c.execute('DELETE FROM barbers')
        c.execute('DELETE FROM services')
        c.execute('DELETE FROM schedule')
        c.execute('DELETE FROM appointments')
        
        # Барбер 1
        c.execute('''INSERT INTO barbers (id, name, phone, code) 
                     VALUES (?, ?, ?, ?)''',
                  (1, 'Александр', '+79991234567', 'B-ARBER003'))
        
        # Услуги барбера 1
        services = [
            (1, 'Мужская стрижка', 'Классическая мужская стрижка', 1500, 45),
            (1, 'Детская стрижка', 'Стрижка для детей', 1200, 30),
            (1, 'Бритьё', 'Бритьё опасной бритвой', 800, 20),
            (1, 'Комплекс', 'Стрижка + бритьё + укладка', 2500, 75)
        ]
        
        for service in services:
            c.execute('''INSERT INTO services (barber_id, name, description, price, duration)
                         VALUES (?, ?, ?, ?, ?)''', service)
        
        # Создаем расписание на 7 дней вперед (8:00 - 20:00, каждые 30 минут)
        today = datetime.now().date()
        
        for day in range(7):
            date = today + timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            
            # Временные слоты: 8:00 - 20:00, каждые 30 минут
            for hour in range(8, 20):
                for minute in [0, 30]:
                    time_str = f"{hour:02d}:{minute:02d}"
                    c.execute('''INSERT INTO schedule (barber_id, date, time, is_available)
                                 VALUES (?, ?, ?, ?)''', 
                             (1, date_str, time_str, 1))
        
        conn.commit()
        print("✅ Тестовые данные созданы")
        print("   👨‍💼 Барбер: Александр (код: B-ARBER003)")
        print("   ✂️  Услуги: 4 услуги")
        print("   ⏰ Расписание: 8:00-20:00, 7 дней вперед")
        
    except Exception as e:
        print(f"⚠️ Ошибка создания тестовых данных: {e}")
        conn.rollback()
    finally:
        conn.close()

# Инициализация БД
init_db()
create_test_data()

# ========== ОБСЛУЖИВАНИЕ СТАТИЧЕСКИХ ФАЙЛОВ ==========
@app.route('/')
def serve_index():
    """Главная страница"""
    return send_from_directory(TEMPLATES_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Обслуживаем все статические файлы"""
    # Проверяем, является ли путь HTML файлом
    if path.endswith('.html'):
        return send_from_directory(TEMPLATES_DIR, path)
    
    # Проверяем CSS файлы
    elif path.startswith('css/') or path.endswith('.css'):
        filename = path.replace('css/', '') if path.startswith('css/') else path
        return send_from_directory(CSS_DIR, filename)
    
    # Проверяем JS файлы
    elif path.startswith('js/') or path.endswith('.js'):
        filename = path.replace('js/', '') if path.startswith('js/') else path
        return send_from_directory(JS_DIR, filename)
    
    # Пробуем найти файл в разных местах
    possible_paths = [
        (TEMPLATES_DIR, path),
        (CSS_DIR, path),
        (JS_DIR, path),
        ('.', path)
    ]
    
    for folder, filename in possible_paths:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            return send_from_directory(folder, filename)
    
    return "File not found", 404

# ========== API ДЛЯ КЛИЕНТОВ ==========
@app.route('/api/barbers', methods=['GET'])
def get_barbers():
    """Получить список барберов"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers")
    barbers = [{'id': row[0], 'name': row[1], 'code': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(barbers)

@app.route('/api/barber/<code>', methods=['GET'])
def get_barber_by_code(code):
    """Получить барбера по коду"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({'success': True, 'barber': {'id': row[0], 'name': row[1], 'code': row[2]}})
    else:
        return jsonify({'success': False, 'error': 'Барбер не найден'}), 404

@app.route('/api/services/<int:barber_id>', methods=['GET'])
def get_barber_services(barber_id):
    """Получить услуги барбера"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute('''SELECT id, name, description, price, duration 
                 FROM services WHERE barber_id = ?''', (barber_id,))
    services = [
        {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'price': row[3],
            'duration': row[4]
        }
        for row in c.fetchall()
    ]
    conn.close()
    return jsonify(services)

@app.route('/api/schedule/<int:barber_id>/<date>', methods=['GET'])
def get_barber_schedule(barber_id, date):
    """Получить расписание барбера на конкретную дату"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    # Получаем доступные временные слоты
    c.execute('''SELECT time, is_available 
                 FROM schedule 
                 WHERE barber_id = ? AND date = ? 
                 ORDER BY time''', (barber_id, date))
    
    times = [
        {'time': row[0], 'available': bool(row[1])}
        for row in c.fetchall()
    ]
    
    conn.close()
    return jsonify({'date': date, 'times': times})

@app.route('/api/book', methods=['POST'])
def create_booking():
    """Создать запись"""
    data = request.json
    
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    try:
        # Проверяем доступность времени
        c.execute('''SELECT is_available FROM schedule 
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['barber_id'], data['date'], data['time']))
        slot = c.fetchone()
        
        if not slot or not slot[0]:
            return jsonify({'success': False, 'error': 'Время уже занято'}), 400
        
        # Бронируем время
        c.execute('''UPDATE schedule 
                     SET is_available = 0, client_phone = ?
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['phone'], data['barber_id'], data['date'], data['time']))
        
        # Создаем запись
        c.execute('''INSERT INTO appointments 
                     (barber_id, service_id, client_name, client_phone, date, time, status)
                     VALUES (?, ?, ?, ?, ?, ?, 'pending')''',
                  (data['barber_id'], data.get('service_id'), 
                   data['name'], data['phone'], data['date'], data['time']))
        
        appointment_id = c.lastrowid
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Запись создана успешно',
            'appointment_id': appointment_id
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

# ========== API ДЛЯ БАРБЕРОВ ==========
@app.route('/api/master/login', methods=['POST'])
def master_login():
    """Вход для барберов"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Простая проверка (в продакшене используйте хеширование!)
    if username == 'barber' and password == '123456':
        conn = sqlite3.connect('barber.db')
        c = conn.cursor()
        c.execute("SELECT id, name, code FROM barbers WHERE code = 'B-ARBER003'")
        barber = c.fetchone()
        conn.close()
        
        if barber:
            return jsonify({
                'success': True,
                'barber': {
                    'id': barber[0],
                    'name': barber[1],
                    'code': barber[2]
                }
            })
    
    return jsonify({'success': False, 'error': 'Неверные данные'}), 401

@app.route('/api/master/appointments/<int:barber_id>', methods=['GET'])
def get_master_appointments(barber_id):
    """Получить записи барбера"""
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute('''SELECT a.id, a.client_name, a.client_phone, a.date, a.time, a.status,
                        s.name as service_name, s.price
                 FROM appointments a
                 LEFT JOIN services s ON a.service_id = s.id
                 WHERE a.barber_id = ?
                 ORDER BY a.date, a.time''', (barber_id,))
    
    appointments = [
        {
            'id': row[0],
            'client_name': row[1],
            'client_phone': row[2],
            'date': row[3],
            'time': row[4],
            'status': row[5],
            'service_name': row[6],
            'price': row[7]
        }
        for row in c.fetchall()
    ]
    
    conn.close()
    return jsonify(appointments)

# ========== ТЕСТОВЫЙ ЭНДПОИНТ ==========
@app.route('/api/test', methods=['GET'])
def test_api():
    """Тестовый endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Сервер Barber Booking работает',
        'timestamp': datetime.now().isoformat(),
        'structure': {
            'templates': os.listdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else 'not found',
            'css': os.listdir(CSS_DIR) if os.path.exists(CSS_DIR) else 'not found',
            'js': os.listdir(JS_DIR) if os.path.exists(JS_DIR) else 'not found'
        }
    })

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 60)
    print("✅ СЕРВЕР ЗАПУЩЕН ДЛЯ TELEGRAM MINI APP")
    print("📌 Структура файлов:")
    print(f"   • templates/: {os.listdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else 'NOT FOUND'}")
    print(f"   • css/: {os.listdir(CSS_DIR) if os.path.exists(CSS_DIR) else 'NOT FOUND'}")
    print(f"   • js/: {os.listdir(JS_DIR) if os.path.exists(JS_DIR) else 'NOT FOUND'}")
    print("=" * 60)
    print("🌐 Доступные маршруты:")
    print("   • / - Главная страница")
    print("   • /api/test - Тест API")
    print("   • /api/barbers - Список барберов")
    print("   • /api/barber/B-ARBER003 - Инфо о барбере")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
