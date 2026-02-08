// Инициализация Telegram Web App
function initTelegramApp() {
    if (window.Telegram && Telegram.WebApp) {
        console.log('📱 Telegram Web App обнаружен');
        
        // Развернуть приложение на весь экран
        Telegram.WebApp.expand();
        Telegram.WebApp.ready();
        
        // Включить кнопку "Назад"
        Telegram.WebApp.BackButton.show();
        Telegram.WebApp.BackButton.onClick(() => {
            window.history.back();
        });
        
        // Получить данные пользователя
        const user = Telegram.WebApp.initDataUnsafe.user;
        const initData = Telegram.WebApp.initData;
        
        if (user && initData) {
            console.log('👤 Данные пользователя Telegram:', user);
            
            // Сохранить данные в localStorage
            localStorage.setItem('telegram_user', JSON.stringify(user));
            localStorage.setItem('telegram_user_id', user.id);
            localStorage.setItem('telegram_init_data', initData);
            
            // Получить профиль через Telegram данные
            getProfileViaTelegram(user.id, initData);
        } else {
            console.warn('⚠️ Данные пользователя не получены из Telegram');
            loadFromLocalStorage();
        }
    } else {
        console.log('🌐 Не в Telegram Web App');
        loadFromLocalStorage();
    }
}

// Получение профиля через Telegram данные
function getProfileViaTelegram(telegramId, initData) {
    console.log('📤 Запрос профиля через Telegram данные...');
    
    fetch(`/api/client/profile?tg_data=${encodeURIComponent(initData)}&telegram_id=${telegramId}`)
        .then(response => response.json())
        .then(data => {
            console.log('✅ Ответ от сервера:', data);
            
            if (data.success) {
                // Сохраняем профиль в localStorage
                localStorage.setItem('user_profile', JSON.stringify(data.profile));
                
                // Обновляем UI
                updateProfileUI(data.profile);
                
                // Загружаем историю записей
                loadAppointmentsHistory(data.profile.telegram_id);
                
                // Обновляем статистику
                if (data.stats) {
                    updateStats(data.stats);
                }
                
                // Показываем историю записей
                if (data.appointments && data.appointments.length > 0) {
                    showAppointmentsHistory(data.appointments);
                } else {
                    showNoAppointments();
                }
                
                // Обновляем информацию о последнем барбере
                if (data.profile && data.profile.last_barber_code) {
                    updateLastBarberInfo(data.profile.last_barber_code);
                }
            } else {
                console.error('❌ Ошибка получения профиля:', data.error);
                createTempProfileFromTelegram(telegramId);
            }
        })
        .catch(error => {
            console.error('❌ Ошибка сети:', error);
            createTempProfileFromTelegram(telegramId);
        });
}

// Создание временного профиля из данных Telegram
function createTempProfileFromTelegram(telegramId) {
    const user = JSON.parse(localStorage.getItem('telegram_user') || '{}');
    
    const tempProfile = {
        telegram_id: telegramId,
        first_name: user.first_name || 'Пользователь',
        last_name: user.last_name || '',
        username: user.username || '',
        photo_url: user.photo_url || '',
        phone: '',
        last_barber
