// js/home.js - Основная логика главной страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏠 Главная страница загружена');
    
    // Автоматическая проверка сессии при загрузке
    checkSessionAndRedirect();
    
    // Инициализация Telegram если есть
    initTelegramWebApp();
});

// Инициализация Telegram Web App
function initTelegramWebApp() {
    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
        console.log('✅ Telegram Web App обнаружен');
        
        const tg = Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        // Сохраняем данные пользователя
        const user = tg.initDataUnsafe?.user;
        if (user) {
            localStorage.setItem('telegram_user', JSON.stringify(user));
            localStorage.setItem('telegram_user_id', user.id.toString());
        }
    }
}

// Проверка сессии и автоматический редирект
function checkSessionAndRedirect() {
    const clientToken = localStorage.getItem('clientToken');
    const clientPhone = localStorage.getItem('clientPhone');
    
    if (clientToken && clientPhone) {
        console.log('🔑 Найдена сессия, проверяем валидность...');
        
        fetch('https://barber-booking-db.onrender.com/api/client/check-session?phone=' + encodeURIComponent(clientPhone))
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    console.log('✅ Сессия активна, перенаправляем в профиль...');
                    // Даем время увидеть главную страницу, затем редирект
                    setTimeout(() => {
                        window.location.href = '/client-profile';
                    }, 1000);
                } else {
                    console.log('❌ Сессия невалидна, очищаем данные');
                    localStorage.removeItem('clientToken');
                    localStorage.removeItem('clientPhone');
                }
            })
            .catch(error => {
                console.error('❌ Ошибка проверки сессии:', error);
            });
    } else {
        console.log('🔐 Нет активной сессии, показываем главную страницу');
    }
}

// Обработчик клика "Я клиент" (дублируется из index.html для надежности)
window.handleClientClick = function() {
    const clientToken = localStorage.getItem('clientToken');
    const clientPhone = localStorage.getItem('clientPhone');
    
    if (clientToken && clientPhone) {
        // Уже авторизован - переходим в профиль
        window.location.href = '/client-profile';
    } else {
        // Показываем окно регистрации (функция из index.html)
        if (typeof openRegistrationModal === 'function') {
            openRegistrationModal();
        }
    }
};

// Выход из системы
window.logoutUser = function() {
    if (confirm('Вы действительно хотите выйти из аккаунта?')) {
        const phone = localStorage.getItem('clientPhone');
        
        if (phone) {
            fetch('https://barber-booking-db.onrender.com/api/client/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone: phone
                })
            })
            .catch(error => {
                console.error('Ошибка при выходе:', error);
            });
        }
        
        // Очищаем только данные сессии
        localStorage.removeItem('clientToken');
        localStorage.removeItem('clientPhone');
        localStorage.removeItem('clientPassword');
        
        // Перенаправляем на главную страницу
        setTimeout(() => {
            window.location.href = '/';
        }, 300);
    }
};
