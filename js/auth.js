// js/auth.js - Обработка форм авторизации
const API_BASE_URL = 'https://barber-booking-db.onrender.com'; // ЯВНО указываем Render сервер

document.addEventListener('DOMContentLoaded', function() {
    // Форма входа для барберов - ИСПРАВЛЕНА ДЛЯ RENDER
    const barberForm = document.getElementById('barberLoginForm');
    if (barberForm) {
        barberForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const code = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('errorMessage');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            if (errorMessage) errorMessage.style.display = 'none';
            
            if (!code || !password) {
                showError('Заполните все поля');
                return;
            }
            
            // Показываем загрузку
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
            submitBtn.disabled = true;
            
            try {
                console.log('Отправка запроса на:', API_BASE_URL + '/api/barber/login');
                console.log('Данные:', { code: code, password: password });
                
                // Логин через API на Render
                const response = await fetch(`${API_BASE_URL}/api/barber/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        code: code,
                        password: password
                    })
                });
                
                console.log('Статус ответа:', response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Ошибка сервера:', errorText);
                    
                    // Пробуем распарсить как JSON
                    try {
                        const errorData = JSON.parse(errorText);
                        throw new Error(errorData.error || 'Ошибка сервера: ' + response.status);
                    } catch {
                        throw new Error('Ошибка сервера: ' + response.status);
                    }
                }
                
                const result = await response.json();
                console.log('Результат входа:', result);
                
                if (result.success) {
                    // Сохраняем токен и данные барбера
                    if (result.token) {
                        localStorage.setItem('barber_token', result.token);
                        console.log('Токен сохранен:', result.token.substring(0, 20) + '...');
                    }
                    if (result.barber) {
                        localStorage.setItem('barber_code', result.barber.code);
                        localStorage.setItem('barber_name', result.barber.name);
                        localStorage.setItem('barber_id', result.barber.id);
                    }
                    
                    showSuccess('Вход выполнен! Перенаправляем...');
                    
                    // ВАЖНО: Перенаправляем с токеном в URL
                    setTimeout(() => {
                        if (result.token) {
                            // Редирект на панель барбера на Render сервере
                            window.location.href = API_BASE_URL + '/barber-panel?token=' + encodeURIComponent(result.token);
                        } else {
                            window.location.href = API_BASE_URL + '/barber-panel';
                        }
                    }, 500);
                } else {
                    showError(result.error || 'Ошибка входа');
                }
            } catch (error) {
                console.error('Ошибка входа:', error);
                showError(error.message || 'Ошибка соединения с сервером');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
            
            function showError(message) {
                if (errorMessage) {
                    errorMessage.textContent = message;
                    errorMessage.style.display = 'block';
                } else {
                    alert(message); // На всякий случай
                }
            }
            
            function showSuccess(message) {
                const successDiv = document.getElementById('successMessage') || createSuccessMessage();
                if (successDiv) {
                    successDiv.textContent = message;
                    successDiv.style.display = 'block';
                }
            }
            
            function createSuccessMessage() {
                const div = document.createElement('div');
                div.id = 'successMessage';
                div.className = 'success-message';
                barberForm.appendChild(div);
                return div;
            }
        });
    }
});

// Проверка авторизации барбера - ИСПРАВЛЕНА ДЛЯ RENDER
async function checkBarberAuth() {
    const token = localStorage.getItem('barber_token');
    
    if (!token) {
        // Проверяем URL параметр
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');
        
        if (urlToken) {
            localStorage.setItem('barber_token', urlToken);
            console.log('Токен из URL сохранен');
        } else {
            // Редирект на страницу логина на Render
            window.location.href = API_BASE_URL + '/barber-login';
            return false;
        }
    }
    
    // Проверяем токен через API
    try {
        console.log('Проверка токена...');
        const response = await fetch(`${API_BASE_URL}/api/barber/check`, {
            headers: {
                'Authorization': 'Bearer ' + (token || localStorage.getItem('barber_token')),
                'Accept': 'application/json'
            }
        });
        
        console.log('Статус проверки:', response.status);
        
        if (response.status === 401) {
            console.log('Токен недействителен');
            localStorage.removeItem('barber_token');
            localStorage.removeItem('barber_code');
            localStorage.removeItem('barber_name');
            localStorage.removeItem('barber_id');
            return false;
        }
        
        if (response.ok) {
            const result = await response.json();
            console.log('Результат проверки:', result);
            
            if (result.authenticated && result.barber) {
                // Сохраняем актуальные данные
                localStorage.setItem('barber_code', result.barber.code);
                localStorage.setItem('barber_name', result.barber.name);
                localStorage.setItem('barber_id', result.barber.id);
                return true;
            }
        }
        
        return false;
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
        return false;
    }
}

// Функция выхода
function logoutBarber() {
    if (confirm('Вы действительно хотите выйти?')) {
        localStorage.removeItem('barber_token');
        localStorage.removeItem('barber_code');
        localStorage.removeItem('barber_name');
        localStorage.removeItem('barber_id');
        window.location.href = API_BASE_URL + '/barber-login';
    }
}

// Проверяем авторизацию на странице панели
if (window.location.href.includes('barber-panel')) {
    document.addEventListener('DOMContentLoaded', async function() {
        const isAuthenticated = await checkBarberAuth();
        if (!isAuthenticated) {
            console.log('Не авторизован, редирект...');
        } else {
            console.log('Авторизован, показываем панель');
        }
    });
}

// Экспорт для использования в других файлах
window.Auth = {
    checkBarberAuth,
    logoutBarber,
    API_BASE_URL: API_BASE_URL
};

