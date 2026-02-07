from flask import Flask, request, jsonify, render_template, send_from_directory
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
print("=" * 60)
print("🚀 ЗАПУСК СЕРВЕРА iWant")
print("=" * 60)

# Текущая директория
current_dir = os.getcwd()
print(f"📌 Текущая рабочая директория: {current_dir}")

# Проверка папок
templates_path = os.path.join(current_dir, 'templates')
static_path = os.path.join(current_dir, 'static')

print(f"📌 Папка templates: {os.path.exists(templates_path)}")
print(f"📌 Папка static: {os.path.exists(static_path)}")

if not os.path.exists(static_path):
    print("📌 Создаю папку static и подпапки...")
    os.makedirs(os.path.join(static_path, 'css'), exist_ok=True)
    os.makedirs(os.path.join(static_path, 'js'), exist_ok=True)
    os.makedirs(os.path.join(static_path, 'images'), exist_ok=True)
    print("✅ Папка static создана")

print("=" * 60)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS barbers
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  phone TEXT,
                  code TEXT UNIQUE,
                  work_days TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY,
                  barber_id INTEGER,
                  client_name TEXT,
                  client_phone TEXT,
                  date TEXT,
                  time TEXT,
                  status TEXT DEFAULT 'pending',
                  FOREIGN KEY(barber_id) REFERENCES barbers(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schedule
                 (id INTEGER PRIMARY KEY,
                  barber_id INTEGER,
                  date TEXT,
                  time TEXT,
                  is_available BOOLEAN DEFAULT 1,
                  client_phone TEXT)''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def create_test_data():
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM barbers')
        c.execute('DELETE FROM schedule')
        
        # Барбер Александр (из вашего скриншота)
        c.execute('''INSERT INTO barbers (id, name, phone, code, work_days) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (1, 'Александр', '+79991234567', 'B-ARBER003', '1,2,3,4,5,6'))
        
        # Тестовый барбер 2
        c.execute('''INSERT INTO barbers (id, name, phone, code, work_days) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (2, 'Иван Иванов', '+79997654321', 'IVAN123', '1,2,3,4,5'))
        
        # Создаем расписание на 14 дней
        today = datetime.now().date()
        times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']
        
        for barber_id in [1, 2]:
            for day in range(14):
                date = today + timedelta(days=day)
                date_str = date.strftime('%Y-%m-%d')
                for time in times:
                    c.execute('''INSERT INTO schedule (barber_id, date, time, is_available)
                                 VALUES (?, ?, ?, ?)''', 
                             (barber_id, date_str, time, 1))
        
        conn.commit()
        print("✅ Тестовые данные созданы")
        print(f"   👨‍💼 Барбер 1: Александр (код: B-ARBER003)")
        print(f"   👨‍💼 Барбер 2: Иван Иванов (код: IVAN123)")
        print(f"   📅 Расписание: 14 дней, 9 временных слотов в день")
    except Exception as e:
        print(f"⚠️ Ошибка создания тестовых данных: {e}")
    finally:
        conn.close()

init_db()
create_test_data()

# ========== СТАТИЧЕСКИЕ ФАЙЛЫ ==========
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ========== HTML СТРАНИЦЫ ==========
@app.route('/')
def index():
    print(f"📄 Запрос: Главная страница")
    return render_template('index.html')

@app.route('/profile')
def profile():
    print(f"📄 Запрос: Страница профиля")
    return render_template('profile.html')

@app.route('/schedule')
def schedule():
    print(f"📄 Запрос: Расписание")
    return render_template('schedule.html')

@app.route('/master-login')
def master_login():
    print(f"📄 Запрос: Вход для клиента")
    return render_template('master-login.html')

@app.route('/master-panel')
def master_panel():
    print(f"📄 Запрос: Панель мастера")
    return render_template('master_panel.html')

# ========== API ДЛЯ КЛИЕНТОВ ==========
@app.route('/api/barbers', methods=['GET'])
def get_barbers():
    print(f"📡 API запрос: Список барберов")
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    c.execute("SELECT id, name, code FROM barbers")
    barbers = [{'id': row[0], 'name': row[1], 'code': row[2]} for row in c.fetchall()]
    conn.close()
    print(f"   Найдено барберов: {len(barbers)}")
    return jsonify(barbers)

@app.route('/api/schedule/<barber_code>', methods=['GET'])
def get_schedule(barber_code):
    print(f"📡 API запрос: Расписание для {barber_code}")
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM barbers WHERE code = ?", (barber_code,))
    barber = c.fetchone()
    
    if not barber:
        print(f"   ❌ Барбер с кодом {barber_code} не найден")
        conn.close()
        return jsonify({'error': 'Барбер не найден'}), 404
    
    barber_id = barber[0]
    print(f"   ✅ Найден барбер ID: {barber_id}")
    
    schedule = []
    today = datetime.now().date()
    
    for day in range(7):
        date = today + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        
        c.execute('''SELECT time, is_available FROM schedule 
                     WHERE barber_id = ? AND date = ? 
                     ORDER BY time''', (barber_id, date_str))
        
        times = []
        rows = c.fetchall()
        for row in rows:
            times.append({
                'time': row[0],
                'available': bool(row[1])
            })
        
        schedule.append({
            'date': date_str,
            'day_name': ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][date.weekday()],
            'times': times
        })
    
    conn.close()
    print(f"   📅 Возвращаем расписание на {len(schedule)} дней")
    return jsonify(schedule)

@app.route('/api/book', methods=['POST'])
def book_appointment():
    print(f"📡 API запрос: Бронирование")
    data = request.json
    print(f"   Данные: {data}")
    
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute('''UPDATE schedule 
                 SET is_available = 0, client_phone = ?
                 WHERE barber_id = ? AND date = ? AND time = ?''',
              (data['phone'], data['barber_id'], data['date'], data['time']))
    
    c.execute('''INSERT INTO bookings (barber_id, client_name, client_phone, date, time, status)
                 VALUES (?, ?, ?, ?, ?, 'pending')''',
              (data['barber_id'], data['name'], data['phone'], 
               data['date'], data['time']))
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Запись создана успешно")
    return jsonify({'success': True, 'message': 'Запись отправлена'})

# ========== API ДЛЯ МАСТЕРОВ ==========
@app.route('/api/master/<code>')
def get_master_by_code(code):
    print(f"📡 API запрос: Данные мастера {code}")
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute('SELECT id, name, phone, code FROM barbers WHERE code = ?', (code,))
    master = c.fetchone()
    conn.close()
    
    if master:
        print(f"   ✅ Мастер найден: {master[1]}")
        return jsonify({
            'success': True,
            'master': {
                'id': master[0],
                'name': master[1],
                'phone': master[2],
                'code': master[3]
            }
        })
    else:
        print(f"   ❌ Мастер с кодом {code} не найден")
        return jsonify({'success': False, 'error': 'Мастер не найден'}), 404

@app.route('/api/master-schedule/<code>')
def get_master_schedule(code):
    print(f"📡 API запрос: Расписание мастера {code}")
    conn = sqlite3.connect('barber.db')
    c = conn.cursor()
    
    c.execute('SELECT id FROM barbers WHERE code = ?', (code,))
    master = c.fetchone()
    
    if not master:
        print(f"   ❌ Мастер с кодом {code} не найден")
        conn.close()
        return jsonify({'error': 'Мастер не найден'}), 404
    
    barber_id = master[0]
    
    schedule = []
    today = datetime.now().date()
    
    for day in range(7):
        date = today + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        
        c.execute('''SELECT time, is_available FROM schedule 
                     WHERE barber_id = ? AND date = ? AND is_available = 1
                     ORDER BY time''', (barber_id, date_str))
        
        times = [row[0] for row in c.fetchall()]
        
        if times:
            day_name = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][date.weekday()]
            schedule.append({
                'date': date_str,
                'day': 'Сегодня' if day == 0 else 'Завтра' if day == 1 else day_name,
                'times': times
            })
    
    conn.close()
    
    stats = {
        'fill_percent': 10,
        'available_hours': '18:30',
        'total_hours': '20:00',
        'cancel_rate': 1.5,
        'completion_rate': 98.5
    }
    
    print(f"   📅 Возвращаем расписание на {len(schedule)} дней")
    return jsonify({
        'schedule': schedule,
        'stats': stats
    })

# ========== ТЕСТОВЫЙ ЭНДПОИНТ ==========
@app.route('/api/test')
def test_api():
    print(f"📡 Тестовый запрос")
    return jsonify({
        'status': 'ok',
        'message': 'Сервер iWant работает',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == '__main__':
    print("=" * 60)
    print("✅ СЕРВЕР ЗАПУЩЕН: http://localhost:5000")
    print("📌 Тестовые ссылки:")
    print("   • http://localhost:5000/ - Главная")
    print("   • http://localhost:5000/master-login - Вход для клиента")
    print("   • http://localhost:5000/profile?code=B-ARBER003 - Профиль")
    print("   • http://localhost:5000/api/barbers - API: Список барберов")
    print("   • http://localhost:5000/api/test - API: Тест")
    print("=" * 60)
    
    app.run(debug=True, port=5000, host='0.0.0.0')
