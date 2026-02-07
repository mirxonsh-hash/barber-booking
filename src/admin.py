import sqlite3
from datetime import datetime, timedelta

# Подключение к базе данных
conn = sqlite3.connect('barber.db')
c = conn.cursor()

def add_barber():
    """Добавить нового барбера"""
    print("\n✂️ ДОБАВЛЕНИЕ НОВОГО БАРБЕРА")
    
    name = input("Введите имя барбера: ")
    phone = input("Введите телефон: ")
    
    # Генерируем простой код
    c.execute("SELECT COUNT(*) FROM barbers")
    count = c.fetchone()[0]
    code = f"barber{count + 1:03d}"  # barber001, barber002 и т.д.
    
    try:
        c.execute("INSERT INTO barbers (name, phone, code) VALUES (?, ?, ?)",
                  (name, phone, code))
        conn.commit()
        print(f"✅ Барбер '{name}' добавлен!")
        print(f"🔑 Код для клиентов: {code}")
        print(f"📞 Телефон: {phone}")
        
        # Создаем расписание на неделю вперед
        create_schedule_for_barber()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def create_schedule_for_barber():
    """Создать расписание для нового барбера"""
    # Найдем ID только что добавленного барбера
    c.execute("SELECT id FROM barbers ORDER BY id DESC LIMIT 1")
    barber_id = c.fetchone()[0]
    
    # Создаем расписание на 7 дней
    today = datetime.now().date()
    work_hours = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']
    
    for day in range(7):
        date = today + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        
        # Добавляем все рабочие часы
        for time in work_hours:
            c.execute('''INSERT OR IGNORE INTO schedule 
                         (barber_id, date, time, is_available) 
                         VALUES (?, ?, ?, 1)''',
                      (barber_id, date_str, time))
    
    conn.commit()
    print("📅 Расписание создано на неделю вперед")

def view_today_bookings():
    """Посмотреть записи на сегодня"""
    print("\n📋 ЗАПИСИ НА СЕГОДНЯ")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    c.execute('''SELECT 
                    b.name as barber_name,
                    bk.client_name,
                    bk.client_phone,
                    bk.time,
                    bk.status
                 FROM bookings bk
                 JOIN barbers b ON bk.barber_id = b.id
                 WHERE bk.date = ?
                 ORDER BY bk.time''', (today,))
    
    bookings = c.fetchall()
    
    if not bookings:
        print("📭 Нет записей на сегодня")
    else:
        print("=" * 50)
        for booking in bookings:
            print(f"\n👤 Барбер: {booking[0]}")
            print(f"👨 Клиент: {booking[1]}")
            print(f"📞 Телефон: {booking[2]}")
            print(f"⏰ Время: {booking[3]}")
            print(f"📊 Статус: {booking[4]}")
            print("-" * 30)
    
    # Показываем свободные окна на сегодня
    print("\n🟢 СВОБОДНЫЕ ОКНА СЕГОДНЯ:")
    c.execute('''SELECT 
                    b.name,
                    s.time
                 FROM schedule s
                 JOIN barbers b ON s.barber_id = b.id
                 WHERE s.date = ? AND s.is_available = 1
                 ORDER BY b.name, s.time''', (today,))
    
    free_slots = c.fetchall()
    
    if not free_slots:
        print("Нет свободных окон")
    else:
        current_barber = ""
        for slot in free_slots:
            if slot[0] != current_barber:
                print(f"\n✂️ {slot[0]}:")
                current_barber = slot[0]
            print(f"  {slot[1]}", end=" ")
        print()

def view_all_bookings():
    """Посмотреть все будущие записи"""
    print("\n📅 ВСЕ БУДУЩИЕ ЗАПИСИ")
    
    c.execute('''SELECT 
                    b.name as barber_name,
                    bk.client_name,
                    bk.client_phone,
                    bk.date,
                    bk.time,
                    bk.status
                 FROM bookings bk
                 JOIN barbers b ON bk.barber_id = b.id
                 WHERE bk.date >= date('now')
                 ORDER BY bk.date, bk.time''')
    
    bookings = c.fetchall()
    
    if not bookings:
        print("📭 Нет будущих записей")
        return
    
    current_date = ""
    for booking in bookings:
        if booking[3] != current_date:
            print(f"\n📅 {booking[3]} ({['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][datetime.strptime(booking[3], '%Y-%m-%d').weekday()]}):")
            current_date = booking[3]
        
        print(f"  ⏰ {booking[4]} - {booking[0]}: {booking[1]} ({booking[2]}) [{booking[5]}]")

def confirm_booking():
    """Подтвердить запись"""
    print("\n✅ ПОДТВЕРЖДЕНИЕ ЗАПИСИ")
    
    client_phone = input("Введите телефон клиента: ")
    
    c.execute('''UPDATE bookings 
                 SET status = 'confirmed'
                 WHERE client_phone = ? AND status = 'pending' AND date >= date('now')''',
              (client_phone,))
    
    if c.rowcount > 0:
        conn.commit()
        print("✅ Запись подтверждена!")
        
        # Получаем данные клиента для звонка
        c.execute('''SELECT client_name, date, time 
                     FROM bookings 
                     WHERE client_phone = ?''', (client_phone,))
        client = c.fetchone()
        
        if client:
            print(f"\n📞 Позвоните клиенту:")
            print(f"   Имя: {client[0]}")
            print(f"   Дата: {client[1]}")
            print(f"   Время: {client[2]}")
    else:
        print("❌ Запись не найдена или уже подтверждена")

def cancel_booking():
    """Отменить запись"""
    print("\n❌ ОТМЕНА ЗАПИСИ")
    
    client_phone = input("Введите телефон клиента: ")
    
    c.execute('''UPDATE bookings 
                 SET status = 'cancelled'
                 WHERE client_phone = ? AND status != 'cancelled' AND date >= date('now')''',
              (client_phone,))
    
    if c.rowcount > 0:
        # Освобождаем время в расписании
        c.execute('''UPDATE schedule 
                     SET is_available = 1, client_phone = NULL
                     WHERE client_phone = ?''', (client_phone,))
        
        conn.commit()
        print("✅ Запись отменена, время освобождено")
    else:
        print("❌ Запись не найдена")

def view_barbers():
    """Посмотреть всех барберов"""
    print("\n👥 СПИСОК БАРБЕРОВ")
    
    c.execute("SELECT id, name, phone, code FROM barbers")
    barbers = c.fetchall()
    
    if not barbers:
        print("Нет барберов в системе")
        return
    
    print("=" * 50)
    for barber in barbers:
        print(f"\nID: {barber[0]}")
        print(f"Имя: {barber[1]}")
        print(f"Телефон: {barber[2]}")
        print(f"Код для клиентов: {barber[3]}")
        print("-" * 30)

def add_manual_booking():
    """Добавить запись вручную"""
    print("\n➕ РУЧНАЯ ЗАПИСЬ")
    
    view_barbers()
    barber_id = input("\nВведите ID барбера: ")
    
    client_name = input("Имя клиента: ")
    client_phone = input("Телефон клиента: ")
    date = input("Дата (ГГГГ-ММ-ДД): ")
    time = input("Время (ЧЧ:ММ): ")
    
    try:
        # Добавляем в бронирования
        c.execute('''INSERT INTO bookings 
                     (barber_id, client_name, client_phone, date, time, status)
                     VALUES (?, ?, ?, ?, ?, 'confirmed')''',
                  (barber_id, client_name, client_phone, date, time))
        
        # Закрываем время в расписании
        c.execute('''UPDATE schedule 
                     SET is_available = 0, client_phone = ?
                     WHERE barber_id = ? AND date = ? AND time = ?''',
                  (client_phone, barber_id, date, time))
        
        conn.commit()
        print("✅ Запись добавлена!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main_menu():
    """Главное меню"""
    while True:
        print("\n" + "=" * 50)
        print("✂️ ПАНЕЛЬ УПРАВЛЕНИЯ БАРБЕРА")
        print("=" * 50)
        print("1. 📋 Записи на сегодня")
        print("2. 📅 Все будущие записи")
        print("3. 👥 Список барберов")
        print("4. ✨ Добавить барбера")
        print("5. ✅ Подтвердить запись")
        print("6. ❌ Отменить запись")
        print("7. ➕ Добавить запись вручную")
        print("8. 💰 Статистика")
        print("9. 🚪 Выход")
        
        choice = input("\nВыберите действие (1-9): ")
        
        if choice == "1":
            view_today_bookings()
        elif choice == "2":
            view_all_bookings()
        elif choice == "3":
            view_barbers()
        elif choice == "4":
            add_barber()
        elif choice == "5":
            confirm_booking()
        elif choice == "6":
            cancel_booking()
        elif choice == "7":
            add_manual_booking()
        elif choice == "8":
            # Простая статистика
            c.execute("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'")
            confirmed = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM bookings WHERE status = 'pending'")
            pending = c.fetchone()[0]
            print(f"\n📊 СТАТИСТИКА:")
            print(f"✅ Подтвержденных записей: {confirmed}")
            print(f"⏳ Ожидают подтверждения: {pending}")
            print(f"💰 Примерный доход: {confirmed * 1500}₽ (при средней цене 1500₽)")
        elif choice == "9":
            print("👋 Выход из системы")
            break
        else:
            print("❌ Неверный выбор")
        
        input("\nНажмите Enter чтобы продолжить...")

if __name__ == "__main__":
    # Создаем таблицы если их нет
    c.execute('''CREATE TABLE IF NOT EXISTS barbers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  code TEXT UNIQUE NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  client_name TEXT NOT NULL,
                  client_phone TEXT NOT NULL,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,
                  status TEXT DEFAULT 'pending',
                  FOREIGN KEY(barber_id) REFERENCES barbers(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schedule
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  barber_id INTEGER NOT NULL,
                  date TEXT NOT NULL,
                  time TEXT NOT NULL,
                  is_available BOOLEAN DEFAULT 1,
                  client_phone TEXT,
                  FOREIGN KEY(barber_id) REFERENCES barbers(id),
                  UNIQUE(barber_id, date, time))''')
    
    conn.commit()
    
    print("=" * 50)
    print("✂️ СИСТЕМА ЗАПИСИ К БАРБЕРУ")
    print("=" * 50)
    
    main_menu()
    
    conn.close()
