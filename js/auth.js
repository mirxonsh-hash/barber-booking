// js/auth.js - Обработка форм авторизации
const API_BASE_URL = window.location.origin; // Автоматически определяем URL сервера

document.addEventListener('DOMContentLoaded', function() {
    // Форма входа для клиентов (по коду)
    const clientForm = document.getElementById('clientLoginForm');
    if (clientForm) {
        clientForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const codeInput = document.getElementById('masterCode');
            const errorMessage = document.getElementById('errorMessage');
            const successMessage = document.getElementById('successMessage');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            const code = codeInput.value.trim();
            
            // Очищаем сообщения
            if (errorMessage) errorMessage.style.display = 'none';
            if (successMessage) successMessage.style.display = 'none';
            
            if (!code) {
                showError('Введите код мастера');
                return;
            }
            
            // Показываем загрузку
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверяем...';
            submitBtn.disabled = true;
            
            try {
                // Проверяем мастера через API
                const response = await fetch(`${API_BASE_URL}/api/barber/${code}`);
                
                if (!response.ok) {
                    throw new Error('Ошибка сети');
                }
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess('Мастер найден! Перенаправляем...');
                    
                    // Сохраняем код в localStorage
                    localStorage.setItem('currentMasterCode', code);
                    
                    // Перенаправляем на страницу профиля мастера
                    setTimeout(() => {
                        window.location.href = `/profile?code=${code}`;
                    }, 1000);
                } else {
                    showError(result.error || 'Мастер не найден');
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
                if (successMessage) {
                    successMessage.textContent = message;
                    successMessage.style.display = 'block';
                }
            }
        });
    }
    
    // Форма входа для барберов
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
                    
                    // Успешный вход - перенаправляем в панель
                    setTimeout(() => {
                        window.location.href = '/barber-panel';
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
    
    // Проверка авторизации на странице барбера
    if (window.location.pathname.includes('barber-panel')) {
        checkBarberAuth();
    }
});

// Проверка авторизации барбера
async function checkBarberAuth() {
    const token = localStorage.getItem('barber_token');
    const barberCode = localStorage.getItem('barber_code');
    
    if (!token && !barberCode) {
        // Редирект на страницу входа
        window.location.href = '/barber-login';
        return;
    }
    
    try {
        // Проверяем авторизацию через API
        const response = await fetch(`${API_BASE_URL}/api/barber/check`, {
            headers: {
                'Authorization': token ? `Bearer ${token}` : '',
                'X-Barber-Code': barberCode || ''
            }
        });
        
        if (response.status === 401) {
            // Не авторизован - очищаем localStorage и редирект
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

// Функция выхода
function logoutBarber() {
    localStorage.removeItem('barber_token');
    localStorage.removeItem('barber_code');
    localStorage.removeItem('barber_name');
    localStorage.removeItem('barber_id');
    window.location.href = '/barber-login';
}

// Добавляем кнопку выхода на страницу barber-panel
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
