// js/auth.js - Обработка форм авторизации
const API_BASE_URL = window.location.origin; // Автоматически определяем URL сервера

document.addEventListener('DOMContentLoaded', function() {
    // Форма входа для клиентов (по коду) - БЕЗ ИЗМЕНЕНИЙ
    
    // Форма входа для барберов - ИСПРАВЛЕНА
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
                // Логин через API
                const response = await fetch(`${API_BASE_URL}/api/barber/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        code: code,
                        password: password
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Ошибка сети');
                }
                
                const result = await response.json();
                
                if (result.success) {
                    // Сохраняем токен и данные барбера
                    if (result.token) {
                        localStorage.setItem('barber_token', result.token);
                    }
                    localStorage.setItem('barber_code', result.barber.code);
                    localStorage.setItem('barber_name', result.barber.name);
                    localStorage.setItem('barber_id', result.barber.id);
                    
                    showSuccess('Вход выполнен! Перенаправляем...');
                    
                    // ВАЖНО: Перенаправляем с токеном в URL
                    setTimeout(() => {
                        if (result.token) {
                            window.location.href = '/barber-panel?token=' + encodeURIComponent(result.token);
                        } else {
                            window.location.href = '/barber-panel';
                        }
                    }, 500);
                } else {
                    showError(result.error || 'Ошибка входа');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showError('Ошибка соединения с сервером');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
            
            function showError(message) {
                if (errorMessage) {
                    errorMessage.textContent = message;
                    errorMessage.style.display = 'block';
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
    
    // Проверка авторизации на странице барбера - ИСПРАВЛЕНА
    if (window.location.pathname.includes('barber-panel')) {
        checkBarberAuth();
    }
});

// Проверка авторизации барбера - ИСПРАВЛЕНА
async function checkBarberAuth() {
    const token = localStorage.getItem('barber_token');
    
    // Проверяем токен в localStorage
    if (!token) {
        // Если нет токена в localStorage, проверяем URL параметр
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');
        
        if (urlToken) {
            // Сохраняем токен из URL в localStorage
            localStorage.setItem('barber_token', urlToken);
            
            // Проверяем токен через API
            try {
                const response = await fetch(`${API_BASE_URL}/api/barber/check`, {
                    headers: {
                        'Authorization': 'Bearer ' + urlToken
                    }
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.authenticated) {
                        // Сохраняем данные барбера
                        localStorage.setItem('barber_code', result.barber.code);
                        localStorage.setItem('barber_name', result.barber.name);
                        localStorage.setItem('barber_id', result.barber.id);
                        return; // Всё ок, остаемся на странице
                    }
                }
            } catch (error) {
                console.error('Ошибка проверки токена:', error);
            }
        }
        
        // Если дошли сюда, значит не авторизованы
        localStorage.removeItem('barber_token');
        localStorage.removeItem('barber_code');
        localStorage.removeItem('barber_name');
        localStorage.removeItem('barber_id');
        window.location.href = '/barber-login';
        return;
    }
    
    // Проверяем существующий токен
    try {
        const response = await fetch(`${API_BASE_URL}/api/barber/check`, {
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
        
        if (response.status === 401) {
            // Токен устарел, редирект на логин
            localStorage.removeItem('barber_token');
            localStorage.removeItem('barber_code');
            localStorage.removeItem('barber_name');
            localStorage.removeItem('barber_id');
            window.location.href = '/barber-login';
        }
    } catch (error) {
        console.error('Ошибка проверки авторизации:', error);
    }
}

// Функция выхода - БЕЗ ИЗМЕНЕНИЙ
function logoutBarber() {
    localStorage.removeItem('barber_token');
    localStorage.removeItem('barber_code');
    localStorage.removeItem('barber_name');
    localStorage.removeItem('barber_id');
    window.location.href = '/barber-login';
}

// Добавляем кнопку выхода - БЕЗ ИЗМЕНЕНИЙ
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('barber-panel')) {
        // Создаем кнопку выхода если её нет
        setTimeout(() => {
            const logoutBtn = document.getElementById('logoutBtn') || document.querySelector('.logout-btn');
            if (logoutBtn) {
                logoutBtn.addEventListener('click', logoutBarber);
            }
        }, 1000);
    }
});
