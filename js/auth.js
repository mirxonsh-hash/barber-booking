// js/auth.js - Обработка форм авторизации
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
                const result = await BarberSystem.checkMasterCode(code);
                
                if (result.success) {
                    showSuccess('Мастер найден! Перенаправляем...');
                    
                    // Сохраняем код в localStorage для использования на странице профиля
                    localStorage.setItem('currentMasterCode', code);
                    
                    // Перенаправляем на страницу профиля мастера
                    setTimeout(() => {
                        window.location.href = `client-profile.html?code=${code}`;
                    }, 1000);
                } else {
                    showError(result.error || 'Мастер не найден');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showError('Ошибка соединения');
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
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('errorMessage');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            if (errorMessage) errorMessage.style.display = 'none';
            
            if (!username || !password) {
                showError('Заполните все поля');
                return;
            }
            
            // Показываем загрузку
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
            submitBtn.disabled = true;
            
            try {
                const result = await BarberSystem.loginBarber(username, password);
                
                if (result.success) {
                    // Успешный вход - перенаправляем в панель
                    setTimeout(() => {
                        window.location.href = 'barber-panel.html';
                    }, 500);
                } else {
                    showError(result.error || 'Ошибка входа');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showError('Ошибка соединения');
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
        });
    }
    
    // Проверка авторизации на защищенных страницах
    const protectedPages = ['barber-panel.html'];
    const currentPage = window.location.pathname.split('/').pop();
    
    if (protectedPages.includes(currentPage) && !BarberSystem.isAuthenticated()) {
        // Если не авторизован - редирект на страницу входа
        window.location.href = 'barber-login.html';
    }
});
