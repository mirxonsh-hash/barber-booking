// js/client-auth.js - Авторизация клиентов
const ClientAuth = {
    API_BASE: 'https://barber-booking-db.onrender.com',
    
    // Проверка сессии
    checkSession: async function() {
        const token = localStorage.getItem('clientToken');
        const phone = localStorage.getItem('clientPhone');
        
        if (!token || !phone) {
            return { authenticated: false, message: 'Нет данных сессии' };
        }
        
        try {
            const response = await fetch(`${this.API_BASE}/api/client/check-session?phone=${encodeURIComponent(phone)}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('❌ Ошибка проверки сессии:', error);
            return { authenticated: false, error: 'Ошибка соединения' };
        }
    },
    
    // Вход по телефону и паролю
    login: async function(phone, password) {
        try {
            const response = await fetch(`${this.API_BASE}/api/client/auth`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone: phone,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Сохраняем в localStorage
                localStorage.setItem('clientToken', data.token);
                localStorage.setItem('clientPhone', data.phone);
                localStorage.setItem('clientId', data.client_id);
                
                return {
                    success: true,
                    message: 'Вход выполнен успешно',
                    token: data.token,
                    phone: data.phone
                };
            } else {
                return {
                    success: false,
                    error: data.error || 'Ошибка входа'
                };
            }
            
        } catch (error) {
            console.error('❌ Ошибка входа:', error);
            return {
                success: false,
                error: 'Ошибка соединения с сервером'
            };
        }
    },
    
    // Регистрация нового клиента
    register: async function(phone, telegramData = null) {
        try {
            const registrationData = {
                phone: phone,
                send_to_telegram: true
            };
            
            if (telegramData) {
                registrationData.telegram_data = telegramData;
            }
            
            const response = await fetch(`${this.API_BASE}/api/client/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(registrationData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Сохраняем данные
                localStorage.setItem('clientPhone', data.phone);
                localStorage.setItem('clientPassword', data.password);
                
                if (data.token) {
                    localStorage.setItem('clientToken', data.token);
                }
                
                return {
                    success: true,
                    message: 'Регистрация успешна',
                    phone: data.phone,
                    password: data.password,
                    token: data.token,
                    is_existing: data.is_existing || false
                };
            } else {
                return {
                    success: false,
                    error: data.error || 'Ошибка регистрации'
                };
            }
            
        } catch (error) {
            console.error('❌ Ошибка регистрации:', error);
            return {
                success: false,
                error: 'Ошибка соединения с сервером'
            };
        }
    },
    
    // Проверка существования номера
    checkPhoneExists: async function(phone) {
        try {
            const response = await fetch(`${this.API_BASE}/api/client/check-phone`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone: phone
                })
            });
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('❌ Ошибка проверки номера:', error);
            return { exists: false, error: 'Ошибка соединения' };
        }
    },
    
    // Получение пароля (восстановление)
    getPassword: async function(phone) {
        try {
            const response = await fetch(`${this.API_BASE}/api/client/get-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone: phone
                })
            });
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('❌ Ошибка получения пароля:', error);
            return { success: false, error: 'Ошибка соединения' };
        }
    },
    
    // Выход
    logout: function() {
        const phone = localStorage.getItem('clientPhone');
        
        if (phone) {
            // Отправляем запрос на сервер о выходе
            fetch(`${this.API_BASE}/api/client/logout`, {
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
        
        // Очищаем данные сессии
        localStorage.removeItem('clientToken');
        localStorage.removeItem('clientPhone');
        localStorage.removeItem('clientId');
        localStorage.removeItem('clientPassword');
        
        // Перенаправляем на главную
        window.location.href = '/';
    },
    
    // Получить текущего клиента
    getCurrentClient: function() {
        const phone = localStorage.getItem('clientPhone');
        const token = localStorage.getItem('clientToken');
        
        return phone ? {
            phone: phone,
            token: token
        } : null;
    },
    
    // Проверить, авторизован ли клиент
    isAuthenticated: function() {
        return !!localStorage.getItem('clientToken') && !!localStorage.getItem('clientPhone');
    },
    
    // Получить данные Telegram
    getTelegramData: function() {
        const initData = localStorage.getItem('telegram_init_data');
        const userData = localStorage.getItem('telegram_user');
        
        return {
            initData: initData,
            user: userData ? JSON.parse(userData) : null
        };
    },
    
    // Форматирование телефона
    formatPhone: function(phone) {
        const cleaned = phone.replace(/\D/g, '');
        
        if (cleaned.startsWith('998')) {
            const match = cleaned.match(/^998(\d{2})(\d{3})(\d{2})(\d{2})$/);
            if (match) {
                return `+998 ${match[1]} ${match[2]} ${match[3]} ${match[4]}`;
            }
        }
        
        return phone;
    },
    
    // Автоматический вход при наличии сессии
    autoLogin: function() {
        const token = localStorage.getItem('clientToken');
        const phone = localStorage.getItem('clientPhone');
        
        if (token && phone) {
            console.log('🔐 Автоматический вход для:', phone);
            
            this.checkSession().then(data => {
                if (data.authenticated) {
                    console.log('✅ Сессия активна');
                    // Можно выполнить дополнительные действия
                } else {
                    console.log('❌ Сессия истекла');
                    this.logout();
                }
            });
        }
    }
};

// Экспортируем для использования
window.ClientAuth = ClientAuth;

// Автоматическая проверка сессии при загрузке
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔐 ClientAuth загружен');
    
    // Автоматический вход если есть сессия
    ClientAuth.autoLogin();
    
    // Проверяем сессию
    ClientAuth.checkSession().then(data => {
        if (data.authenticated) {
            console.log('✅ Клиент авторизован:', data.client.phone);
            
            // Можно обновить UI
            updateUIForAuthenticatedUser(data.client);
        }
    });
});

// Обновление UI для авторизованного пользователя
function updateUIForAuthenticatedUser(client) {
    // Находим элементы для обновления
    const authElements = document.querySelectorAll('.auth-status');
    
    authElements.forEach(element => {
        if (element.classList.contains('show-when-authenticated')) {
            element.style.display = 'block';
        }
        if (element.classList.contains('hide-when-authenticated')) {
            element.style.display = 'none';
        }
    });
    
    // Обновляем информацию о пользователе
    const userPhoneElements = document.querySelectorAll('.user-phone');
    userPhoneElements.forEach(element => {
        element.textContent = ClientAuth.formatPhone(client.phone);
    });
}
