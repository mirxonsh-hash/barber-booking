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
        if (user) {
            console.log('👤 Данные пользователя Telegram:', user);
            
            // Сохранить данные в localStorage
            localStorage.setItem('telegram_user', JSON.stringify(user));
            localStorage.setItem('telegram_user_id', user.id);
            localStorage.setItem('telegram_init_data', Telegram.WebApp.initData);
            
            // Отправить данные на сервер
            sendTelegramDataToServer(user, Telegram.WebApp.initData);
            
            // Показать приветствие
            showWelcomeMessage(user);
        } else {
            console.warn('⚠️ Данные пользователя не получены из Telegram');
            loadFromLocalStorage();
        }
    } else {
        console.log('🌐 Не в Telegram Web App');
        loadFromLocalStorage();
    }
}

// Отправка данных Telegram на сервер
function sendTelegramDataToServer(user, initData) {
    console.log('📤 Отправка данных Telegram на сервер...');
    
    fetch(`/api/telegram/auth?tg_data=${encodeURIComponent(initData)}`)
        .then(response => response.json())
        .then(data => {
            console.log('✅ Ответ от сервера:', data);
            if (data.success && data.profile) {
                localStorage.setItem('user_profile', JSON.stringify(data.profile));
                updateProfileUI(data.profile);
                loadAppointmentsHistory(data.profile.telegram_id || user.id);
            } else {
                console.error('❌ Ошибка аутентификации:', data.error);
                createTempProfile(user);
            }
        })
        .catch(error => {
            console.error('❌ Ошибка сети:', error);
            createTempProfile(user);
        });
}

// Создание временного профиля из данных Telegram
function createTempProfile(user) {
    const tempProfile = {
        telegram_id: user.id,
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        username: user.username || '',
        photo_url: user.photo_url || '',
        phone: '',
        last_barber_code: null,
        created_at: new Date().toISOString()
    };
    
    localStorage.setItem('user_profile', JSON.stringify(tempProfile));
    updateProfileUI(tempProfile);
}

// Загрузка данных из localStorage
function loadFromLocalStorage() {
    const profileStr = localStorage.getItem('user_profile');
    if (profileStr) {
        const profile = JSON.parse(profileStr);
        console.log('📂 Загружен профиль из localStorage:', profile);
        updateProfileUI(profile);
        loadAppointmentsHistory(profile.telegram_id);
    } else {
        console.log('ℹ️ Профиль не найден в localStorage');
        showDefaultUI();
    }
}

// Обновление интерфейса профиля
function updateProfileUI(profile) {
    console.log('🎨 Обновление интерфейса профиля:', profile);
    
    // Имя пользователя
    const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
    const nameElement = document.getElementById('user-name');
    if (nameElement) {
        nameElement.textContent = fullName || 'Пользователь';
        document.title = `${fullName} | Barber Booking`;
    }
    
    // Username
    const usernameElement = document.getElementById('user-username');
    if (usernameElement) {
        usernameElement.textContent = profile.username ? `@${profile.username}` : '';
        usernameElement.style.display = profile.username ? 'block' : 'none';
    }
    
    // Телефон
    const phoneElement = document.getElementById('user-phone');
    if (phoneElement) {
        phoneElement.textContent = profile.phone || 'Не указан';
    }
    
    // Аватар
    const avatarElement = document.getElementById('user-avatar');
    const fallbackElement = document.getElementById('avatar-fallback');
    
    if (profile.photo_url) {
        if (avatarElement) {
            avatarElement.src = profile.photo_url;
            avatarElement.style.display = 'block';
            avatarElement.onerror = function() {
                this.style.display = 'none';
                showAvatarFallback(fallbackElement, profile);
            };
        }
        if (fallbackElement) {
            fallbackElement.style.display = 'none';
        }
    } else {
        if (avatarElement) {
            avatarElement.style.display = 'none';
        }
        showAvatarFallback(fallbackElement, profile);
    }
    
    // Дата регистрации
    const memberSinceElement = document.getElementById('member-since');
    if (memberSinceElement && profile.created_at) {
        const date = new Date(profile.created_at);
        memberSinceElement.textContent = date.toLocaleDateString('ru-RU');
    }
}

// Показать fallback для аватара
function showAvatarFallback(element, profile) {
    if (!element) return;
    
    const initials = (profile.first_name ? profile.first_name[0] : '') + 
                   (profile.last_name ? profile.last_name[0] : '');
    element.textContent = initials || 'U';
    element.style.display = 'flex';
}

// Загрузка истории записей
function loadAppointmentsHistory(telegramId) {
    if (!telegramId) {
        console.warn('⚠️ ID пользователя не указан для загрузки записей');
        showNoAppointments();
        return;
    }
    
    console.log('📋 Загрузка истории записей для ID:', telegramId);
    
    fetch(`/api/client/profile?telegram_id=${telegramId}`)
        .then(response => response.json())
        .then(data => {
            console.log('📊 Данные профиля:', data);
            
            if (data.success) {
                // Обновить статистику
                if (data.stats) {
                    updateStats(data.stats);
                }
                
                // Показать историю записей
                if (data.appointments && data.appointments.length > 0) {
                    showAppointmentsHistory(data.appointments);
                } else {
                    showNoAppointments();
                }
                
                // Обновить информацию о последнем барбере
                if (data.profile && data.profile.last_barber_code) {
                    updateLastBarberInfo(data.profile.last_barber_code);
                }
            } else {
                showNoAppointments();
            }
        })
        .catch(error => {
            console.error('❌ Ошибка загрузки истории:', error);
            showNoAppointments();
        });
}

// Обновление статистики
function updateStats(stats) {
    const totalElement = document.getElementById('total-appointments');
    const completedElement = document.getElementById('completed-appointments');
    
    if (totalElement) totalElement.textContent = stats.total || 0;
    if (completedElement) completedElement.textContent = stats.completed || 0;
}

// Показать историю записей
function showAppointmentsHistory(appointments) {
    const container = document.getElementById('appointments-history');
    if (!container) return;
    
    if (appointments.length === 0) {
        showNoAppointments();
        return;
    }
    
    let html = '';
    
    appointments.forEach(appointment => {
        const date = new Date(appointment.date);
        const formattedDate = date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: 'long',
            year: 'numeric'
        });
        
        const statusText = getStatusText(appointment.status);
        const statusClass = appointment.status || 'active';
        
        html += `
        <div class="appointment-item ${statusClass}">
            <div class="appointment-header">
                <span class="service-name">${appointment.service || 'Услуга'}</span>
                <span class="appointment-status ${statusClass}">${statusText}</span>
            </div>
            <div class="appointment-details">
                <div class="appointment-detail">
                    <i class="fas fa-calendar-alt"></i>
                    <span>${formattedDate} в ${appointment.time || '--:--'}</span>
                </div>
                <div class="appointment-detail">
                    <i class="fas fa-user-tie"></i>
                    <span>${appointment.barber_name || 'Барбер'}</span>
                </div>
                <div class="appointment-detail">
                    <i class="fas fa-ruble-sign"></i>
                    <span>${appointment.price || 0} руб.</span>
                </div>
            </div>
        </div>
        `;
    });
    
    container.innerHTML = html;
}

// Показать сообщение об отсутствии записей
function showNoAppointments() {
    const container = document.getElementById('appointments-history');
    if (container) {
        container.innerHTML = `
            <div class="no-appointments">
                <i class="fas fa-calendar-times fa-3x" style="color: #ccc; margin-bottom: 15px;"></i>
                <p>У вас пока нет записей</p>
                <button class="btn btn-primary" onclick="window.location.href='/client-login'">
                    <i class="fas fa-calendar-plus"></i> Записаться к барберу
                </button>
            </div>
        `;
    }
}

// Показать интерфейс по умолчанию
function showDefaultUI() {
    const nameElement = document.getElementById('user-name');
    if (nameElement) {
        nameElement.textContent = 'Гость';
    }
    showNoAppointments();
}

// Обновить информацию о последнем барбере
function updateLastBarberInfo(barberCode) {
    fetch(`/api/barber/${barberCode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.barber) {
                const lastBarberElement = document.getElementById('last-barber');
                if (lastBarberElement) {
                    lastBarberElement.textContent = data.barber.name || barberCode;
                }
            }
        })
        .catch(error => console.error('Ошибка загрузки барбера:', error));
}

// Показать приветственное сообщение
function showWelcomeMessage(user) {
    if (window.Telegram && Telegram.WebApp) {
        const name = user.first_name || 'Пользователь';
        setTimeout(() => {
            Telegram.WebApp.showAlert(`Привет, ${name}! Добро пожаловать в Barber Booking!`);
        }, 500);
    }
}

// Получить текстовое представление статуса
function getStatusText(status) {
    const statusMap = {
        'active': 'Активна',
        'pending': 'Ожидание',
        'confirmed': 'Подтверждена',
        'completed': 'Выполнена',
        'cancelled': 'Отменена'
    };
    return statusMap[status] || status;
}

// Обработчики кнопок
function setupEventListeners() {
    // Кнопка редактирования профиля
    const editBtn = document.getElementById('edit-profile-btn');
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            alert('Функция редактирования профиля скоро будет доступна!');
        });
    }
    
    // Кнопка новой записи
    const newAppointmentBtn = document.getElementById('new-appointment-btn');
    if (newAppointmentBtn) {
        newAppointmentBtn.addEventListener('click', () => {
            const profileStr = localStorage.getItem('user_profile');
            if (profileStr) {
                const profile = JSON.parse(profileStr);
                if (profile.last_barber_code) {
                    window.location.href = `/client-panel?code=${profile.last_barber_code}`;
                } else {
                    window.location.href = '/client-login';
                }
            } else {
                window.location.href = '/client-login';
            }
        });
    }
    
    // Кнопка выхода
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('Вы уверены, что хотите выйти?')) {
                localStorage.removeItem('user_profile');
                localStorage.removeItem('telegram_user');
                localStorage.removeItem('telegram_user_id');
                localStorage.removeItem('telegram_init_data');
                window.location.href = '/';
            }
        });
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Инициализация страницы профиля...');
    initTelegramApp();
    setupEventListeners();
});
