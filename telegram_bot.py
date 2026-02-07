# telegram_bot.py
import telebot
from telebot import types
import sqlite3
import threading
from datetime import datetime, timedelta

# Токен бота (указанный тобой)
TOKEN = '7662525969:AAF33YcsBM8OmeURyarjx-bNxF9ghOVGRNc'

bot = telebot.TeleBot(TOKEN)

def get_db_connection():
    conn = sqlite3.connect('admin.db')
    conn.row_factory = sqlite3.Row
    return conn

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
👋 Добро пожаловать в iWant - сервис записи к мастеру!

✨ *Доступные команды:*
/start - Начать работу
/book - Записаться к мастеру
/mybookings - Мои записи
/cancel - Отменить запись
/master - Вход для мастеров

📱 Используйте кнопки меню для быстрого доступа к функциям!
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('📅 Записаться')
    btn2 = types.KeyboardButton('👨‍🦱 Мои записи')
    btn3 = types.KeyboardButton('🔍 Найти мастера')
    btn4 = types.KeyboardButton('ℹ️ Помощь')
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    
    bot.send_message(message.chat.id, welcome_text, 
                     parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📅 Записаться')
@bot.message_handler(commands=['book'])
def start_booking(message):
    markup = types.InlineKeyboardMarkup()
    
    conn = get_db_connection()
    barbers = conn.execute('SELECT id, name, specialty FROM barbers').fetchall()
    conn.close()
    
    if not barbers:
        bot.send_message(message.chat.id, "❌ В системе пока нет мастеров.")
        return
    
    for barber in barbers:
        btn_text = f"{barber['name']} - {barber['specialty']}"
        callback_data = f"select_barber_{barber['id']}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    bot.send_message(message.chat.id, "👨‍🦱 Выберите мастера:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_barber_'))
def select_barber(call):
    barber_id = call.data.split('_')[2]
    
    conn = get_db_connection()
    barber = conn.execute('SELECT * FROM barbers WHERE id = ?', (barber_id,)).fetchone()
    conn.close()
    
    if barber:
        # Сохраняем выбранного мастера в временных данных
        user_data[call.from_user.id] = {'barber_id': barber_id}
        
        # Показываем услуги
        markup = types.InlineKeyboardMarkup()
        services = ['Стрижка', 'Бритье', 'Укладка', 'Окрашивание', 'Комплекс']
        for service in services:
            markup.add(types.InlineKeyboardButton(service, 
                                                  callback_data=f"select_service_{service}"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Вы выбрали: *{barber['name']}*\n\n💈 Теперь выберите услугу:",
            parse_mode='Markdown',
            reply_markup=markup
        )

# Глобальный словарь для хранения временных данных пользователей
user_data = {}

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_service_'))
def select_service(call):
    service = call.data.split('_', 2)[2]
    
    if call.from_user.id in user_data:
        user_data[call.from_user.id]['service'] = service
    
    # Запрашиваем дату
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    # Генерируем даты на ближайшие 7 дней
    today = datetime.now()
    dates = []
    for i in range(7):
        date = today + timedelta(days=i+1)
        date_str = date.strftime('%Y-%m-%d')
        display_str = date.strftime('%d.%m')
        dates.append((date_str, display_str))
    
    for date_str, display_str in dates:
        markup.add(types.InlineKeyboardButton(display_str, 
                                              callback_data=f"select_date_{date_str}"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Услуга: *{service}*\n\n📅 Выберите дату:",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_date_'))
def select_date(call):
    date_str = call.data.split('_')[2]
    
    if call.from_user.id in user_data:
        user_data[call.from_user.id]['date'] = date_str
    
    # Показываем доступное время
    markup = types.InlineKeyboardMarkup(row_width=3)
    times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', 
             '16:00', '17:00', '18:00', '19:00', '20:00']
    
    for time in times:
        markup.add(types.InlineKeyboardButton(time, callback_data=f"select_time_{time}"))
    
    display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📅 Дата: *{display_date}*\n\n⏰ Выберите время:",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_time_'))
def select_time(call):
    time = call.data.split('_')[2]
    
    if call.from_user.id in user_data:
        user_data[call.from_user.id]['time'] = time
        
        # Запрашиваем имя
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⏰ Время: *{time}*\n\n📝 Теперь введите ваше имя:",
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(msg, ask_phone)

def ask_phone(message):
    name = message.text
    
    if message.from_user.id in user_data:
        user_data[message.from_user.id]['name'] = name
        
        msg = bot.send_message(message.chat.id, "📱 Теперь введите ваш номер телефона:")
        bot.register_next_step_handler(msg, confirm_booking)

def confirm_booking(message):
    phone = message.text
    
    if message.from_user.id in user_data:
        user_data[message.from_user.id]['phone'] = phone
        
        data = user_data[message.from_user.id]
        
        # Получаем информацию о мастере
        conn = get_db_connection()
        barber = conn.execute('SELECT name FROM barbers WHERE id = ?', 
                             (data['barber_id'],)).fetchone()
        conn.close()
        
        summary = f"""
✅ *Проверьте данные записи:*

👨‍🦱 *Мастер:* {barber['name']}
💈 *Услуга:* {data.get('service', 'Стрижка')}
📅 *Дата:* {data.get('date', '')}
⏰ *Время:* {data.get('time', '')}
👤 *Имя:* {data.get('name', '')}
📱 *Телефон:* {data.get('phone', '')}

Всё верно?
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, записать", callback_data="confirm_yes"),
            types.InlineKeyboardButton("❌ Нет, изменить", callback_data="confirm_no")
        )
        
        bot.send_message(message.chat.id, summary, 
                        parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['confirm_yes', 'confirm_no'])
def handle_confirmation(call):
    if call.data == 'confirm_no':
        # Начинаем заново
        start_booking(call.message)
        return
    
    # Создаем запись в БД
    data = user_data.get(call.from_user.id, {})
    
    if not data:
        bot.answer_callback_query(call.id, "❌ Ошибка: данные не найдены")
        return
    
    try:
        conn = get_db_connection()
        
        # Проверяем доступность времени
        existing = conn.execute(
            '''SELECT id FROM appointments 
               WHERE barber_id = ? AND date = ? AND time = ?''',
            (data['barber_id'], data['date'], data['time'])
        ).fetchone()
        
        if existing:
            bot.answer_callback_query(call.id, "❌ Это время уже занято!")
            conn.close()
            return
        
        # Создаем запись
        conn.execute(
            '''INSERT INTO appointments 
               (barber_id, client_name, client_phone, date, time, service, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (data['barber_id'], data['name'], data['phone'], 
             data['date'], data['time'], data.get('service', 'Стрижка'), 'pending')
        )
        
        conn.commit()
        
        # Получаем данные мастера
        barber = conn.execute('SELECT name, code FROM barbers WHERE id = ?', 
                             (data['barber_id'],)).fetchone()
        conn.close()
        
        # Очищаем временные данные
        if call.from_user.id in user_data:
            del user_data[call.from_user.id]
        
        success_text = f"""
🎉 *Запись успешно создана!*

📋 *Детали:*
• Мастер: {barber['name']}
• Услуга: {data.get('service', 'Стрижка')}
• Дата: {data['date']} в {data['time']}
• Ваш код мастера: `{barber['code']}`

⏳ *Статус:* Ожидает подтверждения мастером

🔄 Используйте /mybookings для просмотра ваших записей.
        """
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=success_text,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Error creating booking: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при создании записи")

@bot.message_handler(func=lambda message: message.text == '👨‍🦱 Мои записи')
@bot.message_handler(commands=['mybookings'])
def show_user_bookings(message):
    try:
        conn = get_db_connection()
        
        # Ищем записи по номеру телефона
        appointments = conn.execute(
        '''SELECT a.*, b.name as barber_name 
   FROM appointments a
   JOIN barbers b ON a.barber_id =
   
# Проблема: нет закрывающих тройных кавычек!