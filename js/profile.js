# В функции init_db(), после создания таблицы barbers добавьте:
try:
    cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='barbers' AND column_name='email'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE barbers ADD COLUMN email VARCHAR(100)")
        logger.info("✅ Добавлена колонка 'email' в таблицу barbers")
except Exception as e:
    logger.error(f"❌ Ошибка добавления колонки email: {e}")

try:
    cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='barbers' AND column_name='bio'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE barbers ADD COLUMN bio TEXT")
        logger.info("✅ Добавлена колонка 'bio' в таблицу barbers")
except Exception as e:
    logger.error(f"❌ Ошибка добавления колонки bio: {e}")

try:
    cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='barbers' AND column_name='address'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE barbers ADD COLUMN address TEXT")
        logger.info("✅ Добавлена колонка 'address' в таблицу barbers")
except Exception as e:
    logger.error(f"❌ Ошибка добавления колонки address: {e}")

try:
    cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='barbers' AND column_name='avatar_url'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE barbers ADD COLUMN avatar_url VARCHAR(255) DEFAULT 'avatar-1'")
        logger.info("✅ Добавлена колонка 'avatar_url' в таблицу barbers")
except Exception as e:
    logger.error(f"❌ Ошибка добавления колонки avatar_url: {e}")

try:
    cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='barbers' AND column_name='updated_at'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE barbers ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        logger.info("✅ Добавлена колонка 'updated_at' в таблицу barbers")
except Exception as e:
    logger.error(f"❌ Ошибка добавления колонки updated_at: {e}")
