// profile.js - Обработка профиля барбера с автоматической авторизацией
const API_BASE_URL = 'https://barber-booking-db.onrender.com';

document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 Инициализация профиля барбера...');
    
    // Сначала проверяем и восстанавливаем авторизацию
    initAuth()
        .then(() => {
            // Инициализация навигации
            initNavigation();
            
            // Инициализация обработчиков событий
            initEventHandlers();
            
            // Загружаем профиль
            loadBarberProfile();
        })
        .catch(error => {
            console.error('Ошибка инициализации:', error);
            redirectToLogin();
        });
});

// Инициализация авторизации
async function initAuth() {
    console.log('🔐 Инициализация авторизации...');
    
    try {
        // Проверяем наличие токена
        let token = localStorage.getItem('barber_token');
        
        // Если нет токена в localStorage, проверяем URL
        if (!token) {
            const urlParams = new URLSearchParams(window.location.search);
            const urlToken = urlParams.get('token');
            
            if (urlToken) {
                console.log('📥 Найден токен в URL');
                token = urlToken;
                localStorage.setItem('barber_token', token);
            }
        }
        
        // Если все еще нет токена, проверяем сессию
        if (!token) {
            console.log('❌ Токен не найден, проверяем сессию...');
            const sessionCheck = await checkSession();
            
            if (sessionCheck.authenticated) {
                console.log('✅ Сессия активна');
                // Сессия активна, продолжаем
                return;
            } else {
                console.log('❌ Сессия не активна, редирект на логин');
                redirectToLogin();
                throw new Error('Не авторизован');
            }
        }
        
        // Проверяем токен через API
        console.log('🔍 Проверка токена через API...');
        const authCheck = await checkToken(token);
        
        if (!authCheck.authenticated) {
            console.log('❌ Токен недействителен');
            
            // Пробуем восстановить сессию
            const sessionCheck = await checkSession();
            if (sessionCheck.authenticated) {
                console.log('✅ Сессия восстановлена');
                return;
            }
            
            localStorage.removeItem('barber_token');
            localStorage.removeItem('barber_code');
            localStorage.removeItem('barber_name');
            localStorage.removeItem('barber_id');
            
            redirectToLogin();
            throw new Error('Токен недействителен');
        }
        
        console.log('✅ Авторизация успешна');
        return;
        
    } catch (error) {
        console.error('Ошибка инициализации авторизации:', error);
        throw error;
    }
}

// Проверка токена через API
async function checkToken(token) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/barber/check`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            timeout: 10000 // 10 секунд таймаут
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Результат проверки токена:', data);
            
            if (data.authenticated && data.barber) {
                // Сохраняем данные
                localStorage.setItem('barber_code', data.barber.code);
                localStorage.setItem('barber_name', data.barber.name);
                localStorage.setItem('barber_id', data.barber.id);
                localStorage.setItem('barber_phone', data.barber.phone || '');
                
                return { authenticated: true, barber: data.barber };
            }
        }
        
        return { authenticated: false };
        
    } catch (error) {
        console.error('Ошибка проверки токена:', error);
        return { authenticated: false };
    }
}

// Проверка сессии через localStorage
async function checkSession() {
    try {
        const barberCode = localStorage.getItem('barber_code');
        const barberName = localStorage.getItem('barber_name');
        const barberId = localStorage.getItem('barber_id');
        
        if (barberCode && barberName && barberId) {
            console.log('✅ Сессия найдена в localStorage');
            return { 
                authenticated: true, 
                barber: {
                    code: barberCode,
                    name: barberName,
                    id: barberId
                }
            };
        }
        
        return { authenticated: false };
        
    } catch (error) {
        console.error('Ошибка проверки сессии:', error);
        return { authenticated: false };
    }
}

// Перенаправление на страницу логина
function redirectToLogin() {
    console.log('🔄 Перенаправление на страницу логина...');
    
    // Сохраняем текущий URL для возврата после логина
    const currentUrl = window.location.href;
    localStorage.setItem('redirect_after_login', currentUrl);
    
    // Перенаправляем на страницу логина
    setTimeout(() => {
        window.location.href = `${API_BASE_URL}/barber-login`;
    }, 1000);
}

// Загрузка профиля барбера
async function loadBarberProfile() {
    console.log('👤 Загрузка профиля барбера...');
    
    try {
        // Показываем загрузку
        showLoading(true);
        
        const barberCode = localStorage.getItem('barber_code');
        const barberName = localStorage.getItem('barber_name');
        const barberId = localStorage.getItem('barber_id');
        
        if (!barberCode || !barberName) {
            console.error('❌ Данные барбера не найдены');
            showNotification('Данные профиля не найдены', 'error');
            return;
        }
        
        // Отображаем основную информацию из localStorage
        document.getElementById('displayName').textContent = barberName || 'Барбер';
        document.getElementById('displayCode').textContent = barberCode || '';
        document.getElementById('profileCode').textContent = barberCode || '';
        
        // Заполняем поля формы
        document.getElementById('inputName').value = barberName || '';
        
        // Загружаем дополнительные данные профиля
        await loadBarberDetails();
        
        // Загружаем статистику
        await loadBarberStats();
        
        // Загружаем дату регистрации
        await loadRegistrationDate();
        
        console.log('✅ Профиль загружен');
        
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
        showNotification('Ошибка загрузки профиля: ' + error.message, 'error');
    } finally {
        // Скрываем загрузку
        showLoading(false);
    }
}

// Показать/скрыть индикатор загрузки
function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    
    if (show) {
        if (!loadingIndicator) {
            // Создаем индикатор загрузки
            const loader = document.createElement('div');
            loader.id = 'loadingIndicator';
            loader.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                backdrop-filter: blur(5px);
            `;
            
            loader.innerHTML = `
                <div style="text-align: center;">
                    <div style="width: 60px; height: 60px; border: 4px solid rgba(255,255,255,0.1); border-radius: 50%; border-top-color: var(--primary-color); animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
                    <p style="color: white; font-size: 16px;">Загрузка профиля...</p>
                </div>
            `;
            
            // Добавляем стили для анимации
            const style = document.createElement('style');
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(loader);
        } else {
            loadingIndicator.style.display = 'flex';
        }
    } else {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

// Загрузка дополнительных данных профиля из базы данных
async function loadBarberDetails() {
    try {
        console.log('🔍 Загрузка деталей профиля...');
        
        const token = localStorage.getItem('barber_token');
        
        if (!token) {
            console.warn('Токен не найден, используем localStorage');
            // Используем данные из localStorage
            const savedProfile = localStorage.getItem('barber_profile_details');
            if (savedProfile) {
                const profile = JSON.parse(savedProfile);
                updateProfileFields(profile);
            }
            return;
        }
        
        // Запрос к API для получения данных профиля
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/details`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });
        
        console.log('Статус загрузки деталей:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Данные профиля:', data);
            
            if (data.success && data.profile) {
                const profile = data.profile;
                
                // Обновляем поля профиля
                updateProfileFields(profile);
                
                // Сохраняем для офлайн-использования
                localStorage.setItem('barber_profile_details', JSON.stringify(profile));
                
                // Сохраняем ID для использования при обновлении
                localStorage.setItem('current_barber_id', profile.id);
            } else {
                throw new Error(data.error || 'Ошибка загрузки профиля');
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
    } catch (error) {
        console.error('Ошибка загрузки деталей:', error);
        
        // Fallback: используем данные из localStorage
        const savedProfile = localStorage.getItem('barber_profile_details');
        if (savedProfile) {
            try {
                const profile = JSON.parse(savedProfile);
                updateProfileFields(profile);
                console.log('✅ Использованы сохраненные данные профиля');
            } catch (e) {
                console.error('Ошибка парсинга сохраненного профиля:', e);
            }
        }
        
        // Показываем предупреждение только если это не первый заход
        if (localStorage.getItem('barber_profile_loaded')) {
            showNotification('Используются сохраненные данные', 'warning');
        }
        
        localStorage.setItem('barber_profile_loaded', 'true');
    }
}

// Обновление полей профиля
function updateProfileFields(profile) {
    // Заполняем дополнительные поля
    document.getElementById('inputPhone').value = profile.phone || '';
    document.getElementById('inputEmail').value = profile.email || '';
    document.getElementById('inputBio').value = profile.bio || '';
    document.getElementById('inputAddress').value = profile.address || '';
    
    // Обновляем аватар если есть
    if (profile.avatar_url) {
        updateAvatarDisplay(profile.avatar_url);
        localStorage.setItem('barber_avatar', profile.avatar_url);
    }
    
    // Обновляем дату регистрации
    if (profile.created_at) {
        const date = new Date(profile.created_at);
        document.getElementById('regDate').textContent = date.toLocaleDateString('ru-RU');
    }
}

// Загрузка статистики барбера
async function loadBarberStats() {
    try {
        console.log('📊 Загрузка статистики...');
        
        const token = localStorage.getItem('barber_token');
        
        if (!token) {
            console.warn('Токен не найден, статистика не загружена');
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/api/barber/stats`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success && data.stats) {
                updateStatsDisplay(data.stats);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        updateStatsDisplay({}); // Устанавливаем значения по умолчанию
    }
}

// Обновление отображения статистики
function updateStatsDisplay(stats) {
    document.getElementById('statAppointments').textContent = stats.total || 0;
    document.getElementById('statRating').textContent = '4.8'; // Пока фиксированный рейтинг
    document.getElementById('statClients').textContent = stats.completed || 0;
    
    // Рассчитываем примерный доход
    const income = (stats.completed || 0) * 1500 + (stats.total || 0) * 800;
    document.getElementById('statIncome').textContent = income.toLocaleString('ru-RU');
}

// Загрузка даты регистрации
async function loadRegistrationDate() {
    try {
        const token = localStorage.getItem('barber_token');
        
        // Используем текущую дату как fallback
        const currentDate = new Date();
        document.getElementById('regDate').textContent = currentDate.toLocaleDateString('ru-RU');
        
        if (!token) return;
        
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/registration`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.created_at) {
                const date = new Date(data.created_at);
                document.getElementById('regDate').textContent = date.toLocaleDateString('ru-RU');
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки даты регистрации:', error);
    }
}

// ========== ОСТАЛЬНЫЕ ФУНКЦИИ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ (с некоторыми улучшениями) ==========

// Обновление отображения аватара
function updateAvatarDisplay(avatarUrl) {
    const avatarDisplay = document.getElementById('avatarDisplay');
    
    if (!avatarDisplay) return;
    
    if (avatarUrl) {
        if (avatarUrl.startsWith('http') || avatarUrl.startsWith('data:')) {
            avatarDisplay.innerHTML = `<img src="${avatarUrl}" alt="Аватар" style="width: 100%; height: 100%; object-fit: cover;">`;
        } else if (avatarUrl.startsWith('avatar-')) {
            const type = avatarUrl.split('-')[1];
            const iconClass = getAvatarIcon(type);
            avatarDisplay.innerHTML = `<i class="${iconClass}"></i>`;
            
            // Устанавливаем цвет фона в зависимости от типа
            const bgColor = getAvatarColor(type);
            avatarDisplay.style.background = bgColor;
        }
    }
}

// Получение иконки для аватара
function getAvatarIcon(type) {
    const icons = {
        '1': 'fas fa-user-tie',
        '2': 'fas fa-cut',
        '3': 'fas fa-crown',
        '4': 'fas fa-star',
        '5': 'fas fa-gem'
    };
    return icons[type] || 'fas fa-user';
}

// Получение цвета для аватара
function getAvatarColor(type) {
    const colors = {
        '1': 'linear-gradient(135deg, #4a6fa5, #3a5a80)',
        '2': 'linear-gradient(135deg, #28a745, #1e7e34)',
        '3': 'linear-gradient(135deg, #ff9800, #e68900)',
        '4': 'linear-gradient(135deg, #9c27b0, #7b1fa2)',
        '5': 'linear-gradient(135deg, #607d8b, #455a64)'
    };
    return colors[type] || 'linear-gradient(135deg, #4a6fa5, #3a5a80)';
}

// Инициализация навигации
function initNavigation() {
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
        
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
            });
        });
    }
}

// Инициализация обработчиков событий
function initEventHandlers() {
    // Кнопка сохранения профиля
    const saveProfileBtn = document.getElementById('saveProfileBtn');
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', saveProfile);
    }
    
    // Кнопка отмены изменений
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            if (confirm('Отменить все изменения?')) {
                loadBarberProfile();
                showNotification('Изменения отменены', 'info');
            }
        });
    }
    
    // Кнопка копирования кода
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', copyBarberCode);
    }
    
    // Кнопка "Поделиться кодом"
    const shareCodeBtn = document.getElementById('shareCodeBtn');
    if (shareCodeBtn) {
        shareCodeBtn.addEventListener('click', shareBarberCode);
    }
    
    // Кнопка смены пароля
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', changePassword);
    }
    
    // Кнопка обновления кода
    const refreshCodeBtn = document.getElementById('refreshCodeBtn');
    if (refreshCodeBtn) {
        refreshCodeBtn.addEventListener('click', refreshBarberCode);
    }
    
    // Кнопка выхода
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logoutBarber();
        });
    }
    
    // Кнопка смены аватара
    const avatarChangeBtn = document.getElementById('avatarChangeBtn');
    if (avatarChangeBtn) {
        avatarChangeBtn.addEventListener('click', openAvatarModal);
    }
    
    // Обработчики модального окна аватара
    const closeAvatarModalBtn = document.getElementById('closeAvatarModalBtn');
    const cancelAvatarBtn = document.getElementById('cancelAvatarBtn');
    const saveAvatarBtn = document.getElementById('saveAvatarBtn');
    
    if (closeAvatarModalBtn) {
        closeAvatarModalBtn.addEventListener('click', closeAvatarModal);
    }
    
    if (cancelAvatarBtn) {
        cancelAvatarBtn.addEventListener('click', closeAvatarModal);
    }
    
    if (saveAvatarBtn) {
        saveAvatarBtn.addEventListener('click', saveAvatar);
    }
    
    // Обработчики вариантов аватара
    document.querySelectorAll('.avatar-option').forEach(option => {
        option.addEventListener('click', function() {
            document.querySelectorAll('.avatar-option').forEach(opt => {
                opt.classList.remove('active');
            });
            this.classList.add('active');
            
            const avatarType = this.dataset.avatar;
            updateAvatarPreview(avatarType);
        });
    });
    
    // Обработчик загрузки файла аватара
    const avatarUpload = document.getElementById('avatarUpload');
    if (avatarUpload) {
        avatarUpload.addEventListener('change', handleAvatarUpload);
    }
    
    // Кнопка экспорта данных
    const exportDataBtn = document.getElementById('exportDataBtn');
    if (exportDataBtn) {
        exportDataBtn.addEventListener('click', exportData);
    }
    
    // Кнопка удаления аккаунта
    const deleteAccountBtn = document.getElementById('deleteAccountBtn');
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', deleteAccount);
    }
}

// Сохранение профиля
async function saveProfile() {
    console.log('💾 Сохранение профиля...');
    
    try {
        const token = localStorage.getItem('barber_token');
        if (!token) {
            showNotification('Ошибка авторизации', 'error');
            return;
        }
        
        // Собираем данные из формы
        const profileData = {
            name: document.getElementById('inputName').value.trim(),
            phone: document.getElementById('inputPhone').value.trim(),
            email: document.getElementById('inputEmail').value.trim(),
            bio: document.getElementById('inputBio').value.trim(),
            address: document.getElementById('inputAddress').value.trim(),
            avatar_url: localStorage.getItem('barber_avatar') || 'avatar-1'
        };
        
        // Валидация
        if (!profileData.name) {
            showNotification('Введите имя', 'error');
            return;
        }
        
        // Показываем индикатор сохранения
        const saveBtn = document.getElementById('saveProfileBtn');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
        saveBtn.disabled = true;
        
        // Отправляем запрос на сервер
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            body: JSON.stringify(profileData)
        });
        
        console.log('Статус сохранения:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                // Обновляем данные в localStorage
                localStorage.setItem('barber_name', profileData.name);
                document.getElementById('displayName').textContent = profileData.name;
                
                // Сохраняем детали профиля
                localStorage.setItem('barber_profile_details', JSON.stringify(profileData));
                
                // Обновляем токен если он есть
                if (result.new_token) {
                    localStorage.setItem('barber_token', result.new_token);
                }
                
                showNotification('Профиль успешно сохранен!', 'success');
            } else {
                showNotification(result.error || 'Ошибка сохранения', 'error');
            }
        } else {
            const errorText = await response.text();
            console.error('Ошибка сервера:', errorText);
            
            // Сохраняем локально как fallback
            localStorage.setItem('barber_name', profileData.name);
            localStorage.setItem('barber_profile_details', JSON.stringify(profileData));
            document.getElementById('displayName').textContent = profileData.name;
            
            showNotification('Сохранено локально (ошибка сервера)', 'warning');
        }
        
    } catch (error) {
        console.error('Ошибка сохранения профиля:', error);
        
        // Сохраняем локально как fallback
        const profileData = {
            name: document.getElementById('inputName').value.trim(),
            phone: document.getElementById('inputPhone').value.trim(),
            email: document.getElementById('inputEmail').value.trim(),
            bio: document.getElementById('inputBio').value.trim(),
            address: document.getElementById('inputAddress').value.trim()
        };
        
        localStorage.setItem('barber_name', profileData.name);
        localStorage.setItem('barber_profile_details', JSON.stringify(profileData));
        document.getElementById('displayName').textContent = profileData.name;
        
        showNotification('Сохранено локально: ' + error.message, 'warning');
        
    } finally {
        // Восстанавливаем кнопку
        const saveBtn = document.getElementById('saveProfileBtn');
        if (saveBtn) {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    }
}

// Копирование кода барбера
function copyBarberCode() {
    const code = document.getElementById('profileCode').textContent;
    
    navigator.clipboard.writeText(code)
        .then(() => {
            const copyBtn = document.getElementById('copyCodeBtn');
            const originalText = copyBtn.innerHTML;
            
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Скопировано';
            copyBtn.classList.add('btn-success');
            
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
                copyBtn.classList.remove('btn-success');
            }, 2000);
            
            showNotification('Код скопирован в буфер обмена', 'success');
        })
        .catch(err => {
            console.error('Ошибка копирования:', err);
            showNotification('Не удалось скопировать код', 'error');
        });
}

// Поделиться кодом барбера
function shareBarberCode() {
    const code = document.getElementById('profileCode').textContent;
    const barberName = localStorage.getItem('barber_name') || 'Барбер';
    const shareText = `Запишитесь к ${barberName} через iWant! Код для записи: ${code}\n\nСайт: ${API_BASE_URL}/client-login`;
    
    if (navigator.share) {
        navigator.share({
            title: `Мой код для записи к ${barberName}`,
            text: shareText,
            url: API_BASE_URL
        }).catch(err => {
            console.log('Ошибка Web Share API:', err);
            fallbackShare(shareText);
        });
    } else {
        fallbackShare(shareText);
    }
}

// Fallback для sharing
function fallbackShare(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
            .then(() => {
                showNotification('Текст скопирован в буфер обмена', 'success');
            })
            .catch(() => {
                prompt('Скопируйте текст для分享:', text);
            });
    } else {
        prompt('Скопируйте текст для分享:', text);
    }
}

// Смена пароля
function changePassword() {
    const currentPassword = prompt('Введите текущий пароль:');
    if (!currentPassword) return;
    
    const newPassword = prompt('Введите новый пароль (минимум 6 символов):');
    if (!newPassword || newPassword.length < 6) {
        alert('Пароль должен содержать минимум 6 символов');
        return;
    }
    
    const confirmPassword = prompt('Повторите новый пароль:');
    if (newPassword !== confirmPassword) {
        alert('Пароли не совпадают');
        return;
    }
    
    // Отправляем запрос на смену пароля
    changePasswordRequest(currentPassword, newPassword);
}

// Запрос на смену пароля
async function changePasswordRequest(currentPassword, newPassword) {
    try {
        const token = localStorage.getItem('barber_token');
        
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/change-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                showNotification('Пароль успешно изменен!', 'success');
            } else {
                showNotification(result.error || 'Ошибка смены пароля', 'error');
            }
        } else {
            showNotification('Функция смены пароля в разработке', 'info');
        }
        
    } catch (error) {
        console.error('Ошибка смены пароля:', error);
        showNotification('Ошибка сервера', 'error');
    }
}

// Обновление кода барбера
async function refreshBarberCode() {
    if (!confirm('Сгенерировать новый код? Старый код перестанет работать. Продолжить?')) {
        return;
    }
    
    try {
        const token = localStorage.getItem('barber_token');
        
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/refresh-code`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success && result.new_code) {
                // Обновляем код во всех местах
                document.getElementById('displayCode').textContent = result.new_code;
                document.getElementById('profileCode').textContent = result.new_code;
                
                // Обновляем в localStorage
                localStorage.setItem('barber_code', result.new_code);
                
                // Обновляем токен если он есть
                if (result.new_token) {
                    localStorage.setItem('barber_token', result.new_token);
                }
                
                showNotification('Новый код сгенерирован!', 'success');
            } else {
                showNotification(result.error || 'Ошибка генерации кода', 'error');
            }
        } else {
            showNotification('Функция смены кода в разработке', 'info');
        }
        
    } catch (error) {
        console.error('Ошибка обновления кода:', error);
        showNotification('Ошибка сервера', 'error');
    }
}

// Открытие модального окна аватара
function openAvatarModal() {
    document.getElementById('avatarModal').style.display = 'flex';
    
    // Устанавливаем текущий аватар в превью
    const currentAvatar = localStorage.getItem('barber_avatar') || 'avatar-1';
    const avatarType = currentAvatar.replace('avatar-', '');
    
    const option = document.querySelector(`.avatar-option[data-avatar="${avatarType}"]`);
    if (option) {
        document.querySelectorAll('.avatar-option').forEach(opt => {
            opt.classList.remove('active');
        });
        option.classList.add('active');
        updateAvatarPreview(avatarType);
    }
}

// Закрытие модального окна аватара
function closeAvatarModal() {
    document.getElementById('avatarModal').style.display = 'none';
}

// Обновление превью аватара
function updateAvatarPreview(type) {
    const preview = document.getElementById('avatarPreview');
    const iconClass = getAvatarIcon(type);
    
    preview.innerHTML = `<i class="${iconClass}"></i>`;
    preview.style.background = getAvatarColor(type);
}

// Обработка загрузки файла аватара
function handleAvatarUpload(event) {
    const file = event.target.files[0];
    
    if (!file) return;
    
    // Проверка типа файла
    if (!file.type.startsWith('image/')) {
        showNotification('Выберите изображение', 'error');
        return;
    }
    
    // Проверка размера (максимум 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showNotification('Файл слишком большой (макс. 5MB)', 'error');
        return;
    }
    
    const reader = new FileReader();
    
    reader.onload = function(e) {
        const preview = document.getElementById('avatarPreview');
        preview.innerHTML = `<img src="${e.target.result}" alt="Превью" style="width: 100%; height: 100%; object-fit: cover;">`;
        
        // Сохраняем в localStorage временно
        localStorage.setItem('temp_avatar', e.target.result);
    };
    
    reader.readAsDataURL(file);
}

// Сохранение аватара
async function saveAvatar() {
    let avatarData = null;
    let avatarType = '1';
    
    // Проверяем, выбран ли файл
    const tempAvatar = localStorage.getItem('temp_avatar');
    if (tempAvatar) {
        avatarData = tempAvatar;
        localStorage.removeItem('temp_avatar');
    } else {
        // Используем выбранный вариант
        const activeOption = document.querySelector('.avatar-option.active');
        if (activeOption) {
            avatarType = activeOption.dataset.avatar;
            avatarData = `avatar-${avatarType}`;
        }
    }
    
    if (!avatarData) {
        showNotification('Выберите аватар', 'error');
        return;
    }
    
    try {
        const token = localStorage.getItem('barber_token');
        
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/avatar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                avatar_url: avatarData
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                // Сохраняем в localStorage
                localStorage.setItem('barber_avatar', avatarData);
                
                // Обновляем отображение
                updateAvatarDisplay(avatarData);
                
                closeAvatarModal();
                showNotification('Аватар обновлен!', 'success');
            } else {
                showNotification(result.error || 'Ошибка сохранения аватара', 'error');
            }
        } else {
            // Если API не работает, сохраняем локально
            localStorage.setItem('barber_avatar', avatarData);
            updateAvatarDisplay(avatarData);
            
            closeAvatarModal();
            showNotification('Аватар сохранен локально', 'success');
        }
        
    } catch (error) {
        console.error('Ошибка сохранения аватара:', error);
        // Сохраняем локально как fallback
        localStorage.setItem('barber_avatar', avatarData);
        updateAvatarDisplay(avatarData);
        
        closeAvatarModal();
        showNotification('Аватар сохранен локально', 'success');
    }
}

// Экспорт данных
function exportData() {
    showNotification('Функция экспорта данных в разработке', 'info');
}

// Удаление аккаунта
function deleteAccount() {
    const confirm1 = confirm('ВНИМАНИЕ: Это действие удалит все ваши данные и аккаунт. Это нельзя отменить. Продолжить?');
    
    if (!confirm1) return;
    
    const confirm2 = prompt('Для подтверждения введите "УДАЛИТЬ АККАУНТ":');
    
    if (confirm2 === 'УДАЛИТЬ АККАУНТ') {
        deleteAccountRequest();
    } else {
        alert('Отменено');
    }
}

// Запрос на удаление аккаунта
async function deleteAccountRequest() {
    try {
        const token = localStorage.getItem('barber_token');
        
        const response = await fetch(`${API_BASE_URL}/api/barber/profile/delete-account`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                // Очищаем localStorage
                localStorage.clear();
                
                showNotification('Аккаунт успешно удален', 'success');
                
                setTimeout(() => {
                    window.location.href = API_BASE_URL + '/barber-login';
                }, 2000);
            } else {
                showNotification(result.error || 'Ошибка удаления аккаунта', 'error');
            }
        } else {
            showNotification('Функция удаления аккаунта в разработке', 'info');
        }
        
    } catch (error) {
        console.error('Ошибка удаления аккаунта:', error);
        showNotification('Ошибка сервера', 'error');
    }
}

// Выход из системы
function logoutBarber() {
    if (confirm('Вы действительно хотите выйти?')) {
        localStorage.removeItem('barber_token');
        localStorage.removeItem('barber_code');
        localStorage.removeItem('barber_name');
        localStorage.removeItem('barber_id');
        localStorage.removeItem('barber_profile_details');
        localStorage.removeItem('barber_avatar');
        
        window.location.href = API_BASE_URL + '/barber-login';
    }
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        max-width: 400px;
        animation: slideIn 0.3s ease;
        padding: 15px 20px;
        border-radius: 8px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    `;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-circle' : 
                 type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon}" style="font-size: 20px;"></i>
        <span>${message}</span>
    `;
    
    // Добавляем стили в зависимости от типа
    switch(type) {
        case 'success':
            notification.style.background = 'rgba(40, 167, 69, 0.2)';
            notification.style.borderColor = 'rgba(40, 167, 69, 0.3)';
            break;
        case 'error':
            notification.style.background = 'rgba(220, 53, 69, 0.2)';
            notification.style.borderColor = 'rgba(220, 53, 69, 0.3)';
            break;
        case 'warning':
            notification.style.background = 'rgba(255, 193, 7, 0.2)';
            notification.style.borderColor = 'rgba(255, 193, 7, 0.3)';
            break;
        default:
            notification.style.background = 'rgba(23, 162, 184, 0.2)';
            notification.style.borderColor = 'rgba(23, 162, 184, 0.3)';
    }
    
    document.body.appendChild(notification);
    
    // Удаляем уведомление через 5 секунд
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        notification.style.opacity = '0';
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Добавляем стили для анимаций и уведомлений в head
document.head.insertAdjacentHTML('beforeend', `
    <style>
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        .btn-success {
            background: var(--success-color) !important;
            border-color: var(--success-color) !important;
        }
        /* Стили для кнопок при наведении */
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .btn:active {
            transform: translateY(0);
        }
    </style>
`);
