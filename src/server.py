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

# ========== ДИАГНОСТИКА ФАЙЛОВОЙ СИСТЕМЫ ==========
print("=" * 80)
print("🔍 ДИАГНОСТИКА ФАЙЛОВОЙ СИСТЕМЫ НА RENDER")
print("=" * 80)

current_dir = os.getcwd()
print(f"📌 Текущая рабочая директория: {current_dir}")
print(f"📌 Содержимое текущей директории: {os.listdir('.')}")

# Проверяем все возможные пути к файлам
possible_paths = [
    '.',  # текущая директория
    '..', # на уровень выше
    '/opt/render/project',
    '/opt/render/project/src',
    os.path.dirname(os.path.abspath(__file__))  # директория где лежит server.py
]

print("📌 Поиск важных папок:")
for path in possible_paths:
    if os.path.exists(path):
        print(f"\n📁 {path}:")
        try:
            files = os.listdir(path)
            # Показываем только первые 10 файлов
            for file in files[:10]:
                print(f"   • {file}")
            if len(files) > 10:
                print(f"   • ... и еще {len(files) - 10} файлов")
        except:
            print(f"   ❌ Не могу прочитать содержимое")

print("=" * 80)

# ========== ФУНКЦИИ ДЛЯ ПОИСКА ФАЙЛОВ ==========
def find_file(filename, extensions=None):
    """Ищет файл в разных местах"""
    if extensions is None:
        extensions = ['']
    
    # Места где ищем файлы
    search_paths = [
        '.', '..', '../..',
        'templates', '../templates', 
        'css', '../css',
        'js', '../js',
        '/opt/render/project',
        '/opt/render/project/src',
        '/opt/render/project/templates'
    ]
    
    for path in search_paths:
        for ext in extensions:
            full_path = os.path.join(path, filename + ext)
            if os.path.exists(full_path):
                print(f"✅ Найден файл {filename}{ext} в {path}")
                return path, filename + ext
    
    print(f"❌ Файл {filename} не найден")
    return None, None

def find_folder(folder_name):
    """Ищет папку в разных местах"""
    search_paths = [
        '.', '..', '../..',
        '/opt/render/project',
        '/opt/render/project/src'
    ]
    
    for path in search_paths:
        full_path = os.path.join(path, folder_name)
        if os.path.exists(full_path):
            print(f"✅ Найдена папка {folder_name} в {path}")
            return path
    
    print(f"❌ Папка {folder_name} не найдена")
    return None

# ========== НАХОДИМ ПУТИ К ПАПКАМ ==========
templates_path = find_folder('templates')
css_path = find_folder('css') or '.'
js_path = find_folder('js') or '.'

print(f"📌 Используемые пути:")
print(f"   • templates: {templates_path or 'НЕ НАЙДЕНА'}")
print(f"   • css: {css_path}")
print(f"   • js: {js_path}")

# ========== БАЗА ДАННЫХ ==========
def get_db_path():
    """Определяем где создавать базу данных"""
    possible_db_paths = [
        'barber.db',
        '/tmp/barber.db',
        os.path.join(current_dir, 'barber.db')
    ]
    
    for db_path in possible_db_paths:
        try:
            # Проверяем можем ли создать файл
            with open(db_path, 'a'):
                pass
            print(f"📌 Будем использовать базу: {db_path}")
            return db_path
        except:
            continue
    
    # Если не нашли подходящий путь, используем текущую директорию
    default_path = os.path.join(current_dir, 'barber.db')
    print(f"⚠️  Использую базу по умолчанию: {default_path}")
    return default_path

def init_db():
    db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Барберы
    c.execute('''CREATE TABLE IF NOT EXISTS barbers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  phone TEXT,
                  code TEXT UNIQUE NOT NULL,
                  work_days TEXT DEFAULT '1,2,3,4,5,6',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
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
                  client_phone TEXT,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id))''')
    
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
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id),
                  FOREIGN KEY(service_id) REFERENCES services(id))''')
    
    conn.commit()
    
    # Создаем тестовые данные если таблицы пустые
    c.execute("SELECT COUNT(*) FROM barbers")
    if c.fetchone()[0] == 0:
        print("📌 Создаю тестовые данные...")
        
        # Тестовый барбер
        c.execute('''INSERT INTO barbers (id, name, phone, code) 
                     VALUES (?, ?, ?, ?)''',
                  (1, 'Александр', '+79991234567', 'B-ARBER003'))
        
        # Тестовые услуги
        test_services = [
            (1, 'Мужская стрижка', 1500, 45),
            (1, 'Детская стрижка', 1200, 30),
            (1, 'Бритьё', 800, 20),
            (1, 'Комплекс', 2500, 75)
        ]
        
        for service in test_services:
            c.execute('''INSERT INTO services (barber_id, name, price, duration)
                         VALUES (?, ?, ?, ?)''', service)
        
        # Расписание на 7 дней
        today = datetime.now().date()
        times = []
        for hour in range(8, 20):  # 8:00 до 19:00
            times.append(f"{hour:02d}:00")
            times.append(f"{hour:02d}:30")
        
        for day in range(7):
            date = today + timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            for time in times:
                c.execute('''INSERT INTO schedule (barber_id, date, time, is_available)
                             VALUES (?, ?, ?, ?)''', (1, date_str, time, 1))
        
        print("✅ Тестовые данные созданы")
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

# Инициализация БД
init_db()

# ========== ОБСЛУЖИВАНИЕ ФАЙЛОВ ==========
@app.route('/')
def index():
    """Главная страница"""
    print(f"📄 Запрос главной страницы")
    
    # Пробуем разные пути к index.html
    possible_paths = [
        ('templates', 'index.html'),
        ('.', 'index.html'),
        ('..', 'index.html'),
        ('../templates', 'index.html'),
        ('/opt/render/project/templates', 'index.html')
    ]
    
    for folder, filename in possible_paths:
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            print(f"✅ Найден index.html в {folder}")
            return send_from_directory(folder, filename)
    
    # Если файл не найден, возвращаем простую страницу
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Barber Booking</title></head>
    <body>
        <h1>Barber Booking System</h1>
        <p>Сервер работает! Но index.html не найден.</p>
        <p><a href="/api/test">Проверить API</a></p>
    </body>
    </html>
    """

@app.route('/<path:filename>')
def serve_file(filename):
    """Обслуживает все файлы"""
    print(f"📄 Запрос файла: {filename}")
    
    # Определяем тип файла и где искать
    if filename.endswith('.html'):
        folders = ['templates', '.', '..', '../templates']
        file_to_send = filename
    elif filename.startswith('css/'):
        folders = ['css', '.', '..', '../css']
        file_to_send = filename.replace('css/', '')
    elif filename.startswith('js/'):
        folders = ['js', '.', '..', '../js']
        file_to_send = filename.replace('js/', '')
    else:
        folders = ['.', 'templates', 'css', 'js']
        file_to_send = filename
    
    # Ищем файл
    for folder in folders:
        filepath = os.path.join(folder, file_to_send)
        if os.path.exists(filepath):
            print(f"✅ Найден в {folder}")
            return send_from_directory(folder, file_to_send)
    
    print(f"❌ Файл не найден: {filename}")
    return "File not found", 404

# ========== API ==========
@app.route('/api/test', methods=['GET'])
def test_api():
    """Тестовый endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Сервер Barber Booking работает',
        'timestamp': datetime.now().isoformat(),
        'current_dir': os.getcwd(),
        'files_in_current_dir': os.listdir('.'),
        'templates_exists': os.path.exists('templates'),
        'templates_files': os.listdir('templates') if os.path.exists('templates') else []
    })

@app.route('/api/barbers', methods=['GET'])
def get_barbers():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers")
    barbers = [{'id': row[0], 'name': row[1], 'code': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(barbers)

@app.route('/api/barber/<code>', methods=['GET'])
def get_barber_by_code(code):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({'success': True, 'barber': {'id': row[0], 'name': row[1], 'code': row[2]}})
    return jsonify({'success': False, 'error': 'Барбер не найден'}), 404

@app.route('/api/services/<int:barber_id>', methods=['GET'])
def get_services(barber_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, name, price, duration FROM services WHERE barber_id = ?", (barber_id,))
    services = [
        {'id': row[0], 'name': row[1], 'price': row[2], 'duration': row[3]}
        for row in c.fetchall()
    ]
    conn.close()
    return jsonify(services)

@app.route('/api/schedule/<int:barber_id>/<date>', methods=['GET'])
def get_schedule(barber_id, date):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''SELECT time, is_available FROM schedule 
                 WHERE barber_id = ? AND date = ? ORDER BY time''', (barber_id, date))
    
    times = [{'time': row[0], 'available': bool(row[1])} for row in c.fetchall()]
    conn.close()
    return jsonify({'date': date, 'times': times})

@app.route('/api/book', methods=['POST'])
def book():
    data = request.json
    
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    
    try:
        # Проверяем доступность
        c.execute('''SELECT is_available FROM schedule 
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['barber_id'], data['date'], data['time']))
        
        slot = c.fetchone()
        if not slot or not slot[0]:
            return jsonify({'success': False, 'error': 'Время занято'}), 400
        
        # Бронируем
        c.execute('''UPDATE schedule SET is_available = 0, client_name = ?, client_phone = ?
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (data['name'], data['phone'], data['barber_id'], data['date'], data['time']))
        
        # Создаем запись
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
        conn = sqlite3.connect(get_db_path())
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
    print("🚀 СЕРВЕР ЗАПУЩЕН")
    print("📌 Доступные маршруты:")
    print("   • / - Главная страница")
    print("   • /client-login.html - Вход клиента")
    print("   • /barber-login.html - Вход барбера")
    print("   • /api/test - Тест API")
    print("   • /api/barbers - Список барберов")
    print("=" * 80)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
