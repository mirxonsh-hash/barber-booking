import asyncio
import secrets
import string
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import psycopg2
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Подключение к БД
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    return psycopg2.connect(DATABASE_URL)

# Генерация пароля
def generate_password(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Генерация кода барбера
def generate_barber_code():
    return f"B-{secrets.token_hex(3).upper()}"

# Создание барбера в БД
def create_barber_in_db(code, password, name, phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Хешируем пароль
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        cursor.execute('''
        INSERT INTO barbers (code, password_hash, name, phone)
        VALUES (%s, %s, %s, %s)
        ''', (code, password_hash, name, phone))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка создания барбера: {e}")
        return False
    finally:
        conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для регистрации барберов в системе iWant.\n\n"
        "📌 Команды:\n"
        "/register - Зарегистрироваться как барбер\n"
        "/help - Помощь"
    )

# Команда /register
async def register_barber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Регистрация барбера\n\n"
        "Отправьте ваше имя:"
    )
    context.user_data['awaiting_name'] = True

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if context.user_data.get('awaiting_name'):
        # Получили имя
        name = update.message.text
        context.user_data['name'] = name
        context.user_data['awaiting_name'] = False
        context.user_data['awaiting_phone'] = True
        
        await update.message.reply_text(
            f"👤 Имя: {name}\n\n"
            f"Теперь отправьте ваш телефон:\n"
            f"Например: +998901234567 или 901234567"
        )
    
    elif context.user_data.get('awaiting_phone'):
        # Получили телефон
        phone = update.message.text
        name = context.user_data['name']
        
        # Генерируем данные
        code = generate_barber_code()
        password = generate_password()
        
        await update.message.reply_text("⏳ Создаю аккаунт...")
        
        # Сохраняем в БД
        if create_barber_in_db(code, password, name, phone):
            # Отправляем данные барберу
            await update.message.reply_text(
                f"✅ Регистрация успешна!\n\n"
                f"👤 Ваш логин: `{code}`\n"
                f"🔑 Ваш пароль: `{password}`\n\n"
                f"🌐 Войдите в личный кабинет:\n"
                f"https://barber-booking-1.onrender.com/barber-login.html\n\n"
                f"⚠️ *Сохраните эти данные!* Пароль нельзя восстановить.\n\n"
                f"📱 Для входа используйте:\n"
                f"• Логин: `{code}`\n"
                f"• Пароль: `{password}`",
                parse_mode='Markdown'
            )
            
            # Отправляем в группу/админу (опционально)
            try:
                admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
                if admin_chat_id:
                    await context.bot.send_message(
                        chat_id=admin_chat_id,
                        text=f"📊 Новый барбер:\nИмя: {name}\nТелефон: {phone}\nКод: {code}"
                    )
            except:
                pass
        else:
            await update.message.reply_text(
                "❌ Ошибка регистрации. Возможно, такой телефон уже зарегистрирован."
            )
        
        # Очищаем данные
        context.user_data.clear()

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Помощь:\n\n"
        "1. /register - регистрация нового барбера\n"
        "2. После регистрации вы получите логин и пароль\n"
        "3. Войдите в личный кабинет по ссылке\n"
        "4. В кабинете вы можете:\n"
        "   • Смотреть записи\n"
        "   • Управлять расписанием\n"
        "   • Принимать клиентов\n\n"
        "📞 Поддержка: @ваш_аккаунт"
    )

# Главная функция
def main():
    # Получаем токен из переменных окружения
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения")
        return
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register_barber))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
