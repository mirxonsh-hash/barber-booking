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

# ========== ДИАГНОСТИКА ==========
print("=" * 80)
print("🚀 ЗАПУСК СЕРВЕРА BARBER BOOKING")
print("=" * 80)

current_dir = os.getcwd()
print(f"📌 Текущая директория: {current_dir}")

# Проверяем что есть вокруг
print(f"📌 Содержимое текущей директории:")
for item in os.listdir('.'):
    print(f"   • {item}")

print(f"📌 Содержимое родительской директории:")
try:
    for item in os.listdir('..'):
        print(f"   • {item}")
except:
    print("   ❌ Не могу прочитать")

# ========== ФУНКЦИИ ПОИСКА ФАЙЛОВ ==========
def find_file_anywhere(filename):
    """Ищет файл везде"""
    search_paths = [
        '.',  # текущая
        '..', # на уровень выше
        '../..', # на два уровня выше
        'templates', '../templates', '../../templates',
        '/opt/render/project',
        '/opt/render/project/src',
        '/opt/render/project/templates'
    ]
    
    for path in search_paths:
        filepath = os.path.join(path, filename)
        if os.path.exists(filepath):
            print(f"✅ Найден {filename} в {path}")
            return path
    
    print(f"❌ Файл {filename} не найден нигде")
    return None

# Ищем index.html
html_path = find_file_anywhere('index.html')
css_path = find_file_anywhere('common.css')
js_path = find_file_anywhere('home.js')

print(f"📌 Результаты поиска:")
print(f"   • index.html: {html_path or 'НЕ НАЙДЕН'}")
print(f"   • common.css: {css_path or 'НЕ НАЙДЕН'}")
print(f"   • home.js: {js_path or 'НЕ НАЙДЕН'}")

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
                  work_days TEXT DEFAULT '1,2,3,4,5,6')''')
    
    # Услуги
    c.execute('''CREATE TABLE IF NOT EXISTS services
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  price INTEGER NOT NULL,
                  duration INTEGER NOT NULL,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id))''')
    
    # Расписание (8:00-20:00)
    c.execute('''CREATE TABLE IF NOT EXISTS schedule
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,
                  is_available BOOLEAN DEFAULT 1,
                  client_name TEXT,
                  client_phone TEXT)''')
    
    # Записи
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  service_id INTEGER,
                  client_name TEXT NOT NULL,
                  client_phone TEXT NOT NULL,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,
                  status TEXT DEFAULT 'pending',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    
    # Тестовые данные
    c.execute("SELECT COUNT(*) FROM barbers")
    if c.fetchone()[0] == 0:
        print("📌 Создаю тестовые данные...")
        
        # Барбер
        c.execute('''INSERT INTO barbers (id, name, phone, code) 
                     VALUES (?, ?, ?, ?)''',
                  (1, 'Александр', '+79991234567', 'B-ARBER003'))
        
        # Услуги
        services = [
            (1, 'Мужская стрижка', 1500, 45),
            (1, 'Детская стрижка', 1200, 30),
            (1, 'Бритьё', 800, 20),
            (1, 'Комплекс', 2500, 75)
        ]
        
        for service in services:
            c.execute('''INSERT INTO services (barber_id, name, price, duration)
                         VALUES (?, ?, ?, ?)''', service)
        
        # Расписание
        today = datetime.now().date()
        times = []
        for hour in range(8, 20):
            times.append(f"{hour:02d}:00")
            times.append(f"{hour:02d}:30")
        
        for day in range(7):
            date = today + timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            for time in times:
                c.execute('''INSERT INTO schedule (barber_id, date, time, is_available)
                             VALUES (?, ?, ?, ?)''', (1, date_str, time, 1))
        
        conn.commit()
        print("✅ Тестовые данные созданы")
    
    conn.close()
    print("✅ База данных готова")

init_db()

# ========== ОБСЛУЖИВАНИЕ ФАЙЛОВ ==========
@app.route('/')
def index():
    """Главная страница - ВАЖНО: используем send_from_directory, НЕ render_template"""
    print(f"📄 Запрос главной страницы")
    
    # Пробуем найти index.html
    search_paths = [
        ('templates', 'index.html'),
        ('.', 'index.html'),
        ('..', 'index.html'),
        ('../templates', 'index.html'),
        ('../../templates', 'index.html')
    ]
    
    for folder, filename in search_paths:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            print(f"✅ Отдаю index.html из {folder}")
            return send_from_directory(folder, filename)
    
    # Если не нашли, возвращаем простую HTML
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Barber Booking</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>Barber Booking System</h1>
        <p>✅ Сервер работает!</p>
        <p>Но index.html не найден в ожидаемых местах.</p>
        <p>Проверьте:</p>
        <ul>
            <li><a href="/api/test">API тест</a></li>
            <li><a href="/client-login.html">Вход клиента</a></li>
            <li><a href="/barber-login.html">Вход барбера</a></li>
        </ul>
    </body>
    </html>
    """

@app.route('/<path:filename>')
def serve_file(filename):
    """Обслуживает все файлы"""
    print(f"📄 Запрос файла: {filename}")
    
    # Определяем где искать
    if filename.endswith('.html'):
        folders = ['templates', '.', '..', '../templates']
    elif filename.startswith('css/'):
        folders = ['css', '.', '..', '../css']
        filename = filename.replace('css/', '')
    elif filename.startswith('js/'):
        folders = ['js', '.', '..', '../js']
        filename = filename.replace('js/', '')
    else:
        folders = ['.', 'templates', 'css', 'js']
    
    # Ищем файл
    for folder in folders:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            print(f"✅ Найден в {folder}")
            return send_from_directory(folder, filename)
    
    print(f"❌ Файл не найден: {filename}")
    return f"File {filename} not found", 404

# ========== API ==========
@app.route('/api/test')
def test_api():
    """Тестовый endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Сервер Barber Booking работает',
        'timestamp': datetime.now().isoformat(),
        'current_dir': current_dir,
        'files_here': os.listdir('.'),
        'has_templates': os.path.exists('templates'),
        'has_index_html': os.path.exists('index.html') or os.path.exists('templates/index.html')
    })

@app.route('/api/barbers')
def get_barbers():
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers")
    barbers = [{'id': row[0], 'name': row[1], 'code': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(barbers)

@app.route('/api/barber/<code>')
def get_barber(code):
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({'success': True, 'barber': {'id': row[0], 'name': row[1], 'code': row[2]}})
    return jsonify({'success': False, 'error': 'Барбер не найден'}), 404

@app.route('/api/services/<int:barber_id>')
def get_services(barber_id):
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, price, duration FROM services WHERE barber_id = ?", (barber_id,))
    services = [{'id': row[0], 'name': row[1], 'price': row[2], 'duration': row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(services)

@app.route('/api/schedule/<int:barber_id>/<date>')
def get_schedule(barber_id, date):
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute('''SELECT time, is_available FROM schedule 
                 WHERE barber_id = ? AND date = ? ORDER BY time''', (barber_id, date))
    
    times = [{'time': row[0], 'available': bool(row[1])} for row in c.fetchall()]
    conn.close()
    return jsonify({'date': date, 'times': times})

@app.route('/api/book', methods=['POST'])
def book():
    data = request.json
    
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    try:
        # Проверка доступности
        c.execute('''SELECT is_available FROM schedule 
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['barber_id'], data['date'], data['time']))
        
        slot = c.fetchone()
        if not slot or not slot[0]:
            return jsonify({'success': False, 'error': 'Время занято'}), 400
        
        # Бронирование
        c.execute('''UPDATE schedule SET is_available = 0, client_name = ?, client_phone = ?
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['name'], data['phone'], data['barber_id'], data['date'], data['time']))
        
        # Запись
        c.execute('''INSERT INTO bookings (barber_id, service_id, client_name, client_phone, date, time)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['barber_id'], data.get('service_id'), data['name'], 
                   data['phone'], data['date'], data['time']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Запись создана'})
    
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/master/login', methods=['POST'])
def master_login():
    data = request.json
    
    if data.get('username') == 'barber' and data.get('password') == '123456':
        conn = sqlite3.connect('barber.db')
        c = conn.cursor()
        c.execute("SELECT id, name, code FROM barbers WHERE code = 'B-ARBER003'")
        barber = c.fetchone()
        conn.close()
        
        if barber:
            return jsonify({
                'success': True,
                'barber': {'id': barber[0], 'name': barber[1], 'code': barber[2]}
            })
    
    return jsonify({'success': False, 'error': 'Неверные данные'}), 401

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 80)
    print("🌐 СЕРВЕР ЗАПУЩЕН")
    print("📌 Доступные маршруты:")
    print("   • / - Главная страница")
    print("   • /client-login.html - Вход клиента")
    print("   • /barber-login.html - Вход барбера")
    print("   • /master-login.html - Вход мастера")
    print("   • /api/test - Тест API")
    print("   • /api/barbers - Список барберов")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ... остальной код ...

# Проверка барбера
def verify_barber(code, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute('''
    SELECT id, name FROM barbers 
    WHERE code = %s AND password_hash = %s
    ''', (code, password_hash))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {'id': result[0], 'name': result[1]}
    return None

# Получение записей барбера
def get_barber_appointments(barber_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM appointments 
    WHERE barber_code = %s 
    ORDER BY appointment_date DESC, appointment_time DESC
    ''', (barber_code,))
    
    appointments = cursor.fetchall()
    conn.close()
    
    return appointments

# ... остальные маршруты ...
import threading
from telegram_bot import main as run_bot

# Запускаем бота в отдельном потоке
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
