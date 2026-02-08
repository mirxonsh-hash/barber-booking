// Проверяем, открыто ли приложение в Telegram
if (window.Telegram && Telegram.WebApp) {
    console.log('Telegram Web App detected!');
    
    // Инициализируем Telegram Web App
    Telegram.WebApp.ready();
    
    // Развернуть приложение на весь экран
    Telegram.WebApp.expand();
    
    // Получаем данные пользователя из Telegram
    const user = Telegram.WebApp.initDataUnsafe.user;
    
    if (user) {
        console.log('Telegram user data:', user);
        console.log('User ID:', user.id);
        console.log('First name:', user.first_name);
        console.log('Last name:', user.last_name);
        console.log('Username:', user.username);
        console.log('Photo URL:', user.photo_url);
        
        // Сохраняем данные пользователя в localStorage для использования на других страницах
        localStorage.setItem('telegram_user', JSON.stringify(user));
        localStorage.setItem('telegram_user_id', user.id);
        localStorage.setItem('telegram_init_data', Telegram.WebApp.initData);
        
        // Отправляем данные на сервер для аутентификации
        const initData = Telegram.WebApp.initData;
        console.log('Telegram initData length:', initData.length);
        
        // Показываем уведомление
        Telegram.WebApp.showAlert('Добро пожаловать, ' + (user.first_name || 'Пользователь') + '!');
        
        // Отправляем запрос на сервер
        fetch(`/api/telegram/auth?tg_data=${encodeURIComponent(initData)}`)
            .then(response => {
                console.log('Auth response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Auth response data:', data);
                if (data.success) {
                    console.log('Telegram auth successful!');
                    // Сохраняем профиль в localStorage
                    if (data.profile) {
                        localStorage.setItem('user_profile', JSON.stringify(data.profile));
                    }
                    // Загружаем профиль с использованием telegram_id
                    if (typeof loadClientProfile === 'function') {
                        loadClientProfile(user.id);
                    } else {
                        // Если функция не определена, обновляем UI напрямую
                        updateUserInfo(data.profile);
                    }
                } else {
                    console.error('Telegram auth failed:', data.error);
                    // Создаем профиль локально из данных Telegram
                    const tempProfile = {
                        telegram_id: user.id,
                        first_name: user.first_name || '',
                        last_name: user.last_name || '',
                        username: user.username || '',
                        photo_url: user.photo_url || '',
                        phone: '',
                        last_barber_code: null
                    };
                    localStorage.setItem('user_profile', JSON.stringify(tempProfile));
                    updateUserInfo(tempProfile);
                }
            })
            .catch(error => {
                console.error('Telegram auth error:', error);
                // Создаем профиль локально из данных Telegram
                const tempProfile = {
                    telegram_id: user.id,
                    first_name: user.first_name || '',
                    last_name: user.last_name || '',
                    username: user.username || '',
                    photo_url: user.photo_url || '',
                    phone: '',
                    last_barber_code: null
                };
                localStorage.setItem('user_profile', JSON.stringify(tempProfile));
                updateUserInfo(tempProfile);
            });
    } else {
        console.warn('No user data in Telegram Web App');
        // Проверяем, есть ли сохраненный профиль в localStorage
        const savedProfile = localStorage.getItem('user_profile');
        if (savedProfile) {
            const profile = JSON.parse(savedProfile);
            updateUserInfo(profile);
        }
    }
    
    // Обработчик для кнопки "назад" в Telegram
    Telegram.WebApp.BackButton.onClick(function() {
        window.history.back();
    });
    
    // Показываем кнопку "назад" если это необходимо
    if (window.history.length > 1) {
        Telegram.WebApp.BackButton.show();
    }
} else {
    console.log('Not in Telegram Web App');
    // Проверяем, есть ли сохраненный профиль в localStorage
    const savedProfile = localStorage.getItem('user_profile');
    if (savedProfile) {
        const profile = JSON.parse(savedProfile);
        updateUserInfo(profile);
    }
}

// Функция для обновления информации о пользователе на странице
function updateUserInfo(profile) {
    console.log('Updating user info with profile:', profile);
    
    // Обновляем имя пользователя
    if (profile.first_name || profile.last_name) {
        const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
        const nameElements = document.querySelectorAll('.user-name, #user-name, .client-name');
        nameElements.forEach(el => {
            if (el.tagName === 'INPUT') {
                el.value = fullName;
            } else {
                el.textContent = fullName;
            }
        });
        
        // Обновляем заголовок страницы
        document.title = fullName + ' | Barber Booking';
    }
    
    // Обновляем username
    if (profile.username) {
        const usernameElements = document.querySelectorAll('.user-username, #user-username, .client-username');
        usernameElements.forEach(el => {
            el.textContent = '@' + profile.username;
        });
    }
    
    // Обновляем аватарку
    if (profile.photo_url) {
        const avatarElements = document.querySelectorAll('.user-avatar, .client-avatar, .profile-avatar, img[src*="avatar"]');
        avatarElements.forEach(el => {
            el.src = profile.photo_url;
            el.onerror = function() {
                // Если фото не загружается, используем инициалы
                this.style.display = 'none';
                const fallback = document.createElement('div');
                fallback.className = 'avatar-fallback';
                const initials = (profile.first_name ? profile.first_name[0] : '') + (profile.last_name ? profile.last_name[0] : '');
                fallback.textContent = initials || 'U';
                this.parentNode.appendChild(fallback);
            };
        });
    }
    
    // Обновляем телефон (если есть)
    if (profile.phone) {
        const phoneElements = document.querySelectorAll('.user-phone, #user-phone, .client-phone');
        phoneElements.forEach(el => {
            if (el.tagName === 'INPUT') {
                el.value = profile.phone;
            } else {
                el.textContent = profile.phone;
            }
        });
    }
    
    // Обновляем скрытые поля в формах
    document.querySelectorAll('input[name="telegram_id"], input[name="user_id"]').forEach(el => {
        el.value = profile.telegram_id || '';
    });
    
    // Заполняем поля формы создания записи
    if (profile.first_name || profile.last_name) {
        const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
        document.querySelectorAll('input[name="client_name"], #client-name').forEach(el => {
            el.value = fullName;
        });
    }
    
    if (profile.phone) {
        document.querySelectorAll('input[name="client_phone"], #client-phone').forEach(el => {
            el.value = profile.phone;
        });
    }
}

// Функция для загрузки полного профиля с сервера
function loadClientProfile(telegramId) {
    console.log('Loading client profile for ID:', telegramId);
    
    // Получаем данные из Telegram если есть
    let tgData = '';
    if (window.Telegram && Telegram.WebApp) {
        tgData = Telegram.WebApp.initData;
    }
    
    // Запрашиваем профиль с сервера
    fetch(`/api/client/profile?telegram_id=${telegramId}&tg_data=${encodeURIComponent(tgData)}`)
        .then(response => response.json())
        .then(data => {
            console.log('Profile data:', data);
            if (data.success && data.profile) {
                // Сохраняем профиль в localStorage
                localStorage.setItem('user_profile', JSON.stringify(data.profile));
                // Обновляем UI
                updateUserInfo(data.profile);
                
                // Если есть история записей, отображаем её
                if (data.appointments && data.appointments.length > 0) {
                    displayAppointmentsHistory(data.appointments);
                }
                
                // Если есть статистика, отображаем её
                if (data.stats) {
                    displayUserStats(data.stats);
                }
            } else {
                console.warn('Profile not found or error:', data.error);
                // Используем данные из Telegram
                if (window.Telegram && Telegram.WebApp.initDataUnsafe.user) {
                    const user = Telegram.WebApp.initDataUnsafe.user;
                    const tempProfile = {
                        telegram_id: user.id,
                        first_name: user.first_name || '',
                        last_name: user.last_name || '',
                        username: user.username || '',
                        photo_url: user.photo_url || '',
                        phone: '',
                        last_barber_code: null
                    };
                    localStorage.setItem('user_profile', JSON.stringify(tempProfile));
                    updateUserInfo(tempProfile);
                }
            }
        })
        .catch(error => {
            console.error('Error loading profile:', error);
        });
}

// Функция для отображения истории записей
function displayAppointmentsHistory(appointments) {
    console.log('Displaying appointments history:', appointments);
    
    const historyContainer = document.getElementById('appointments-history');
    if (!historyContainer) return;
    
    if (appointments.length === 0) {
        historyContainer.innerHTML = '<p class="no-appointments">У вас пока нет записей</p>';
        return;
    }
    
    let html = '<div class="appointments-list">';
    appointments.forEach(appointment => {
        const date = new Date(appointment.date);
        const formattedDate = date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        
        html += `
        <div class="appointment-item ${appointment.status}">
            <div class="appointment-header">
                <span class="service-name">${appointment.service || 'Услуга'}</span>
                <span class="appointment-status ${appointment.status}">${getStatusText(appointment.status)}</span>
            </div>
            <div class="appointment-details">
                <div class="appointment-date">
                    <i class="icon-calendar"></i>
                    ${formattedDate} в ${appointment.time || '--:--'}
                </div>
                <div class="appointment-barber">
                    <i class="icon-barber"></i>
                    ${appointment.barber_name || 'Барбер'}
                </div>
                <div class="appointment-price">
                    <i class="icon-price"></i>
                    ${appointment.price || 0} руб.
                </div>
            </div>
        </div>
        `;
    });
    html += '</div>';
    
    historyContainer.innerHTML = html;
}

// Функция для отображения статистики пользователя
function displayUserStats(stats) {
    console.log('Displaying user stats:', stats);
    
    // Обновляем счетчики на странице
    const totalElement = document.getElementById('total-appointments');
    const completedElement = document.getElementById('completed-appointments');
    
    if (totalElement) totalElement.textContent = stats.total || 0;
    if (completedElement) completedElement.textContent = stats.completed || 0;
}

// Функция для получения текстового представления статуса
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

// Функция для отправки данных профиля на сервер
function saveUserProfile(profileData) {
    console.log('Saving user profile:', profileData);
    
    return fetch('/api/client/profile/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Save profile response:', data);
        if (data.success) {
            // Обновляем локальный профиль
            const savedProfile = localStorage.getItem('user_profile');
            if (savedProfile) {
                const currentProfile = JSON.parse(savedProfile);
                const updatedProfile = { ...currentProfile, ...profileData };
                localStorage.setItem('user_profile', JSON.stringify(updatedProfile));
                updateUserInfo(updatedProfile);
            }
            
            // Показываем уведомление об успехе
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.showAlert('Профиль успешно сохранен!');
            } else {
                alert('Профиль успешно сохранен!');
            }
        }
        return data;
    })
    .catch(error => {
        console.error('Error saving profile:', error);
        return { success: false, error: 'Ошибка при сохранении профиля' };
    });
}

// Функция для заполнения формы создания записи данными из профиля
function fillAppointmentFormWithProfile() {
    const profileStr = localStorage.getItem('user_profile');
    if (!profileStr) return;
    
    const profile = JSON.parse(profileStr);
    
    // Заполняем имя
    if (profile.first_name || profile.last_name) {
        const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
        const nameInput = document.getElementById('client-name') || document.querySelector('input[name="client_name"]');
        if (nameInput) nameInput.value = fullName;
    }
    
    // Заполняем телефон
    if (profile.phone) {
        const phoneInput = document.getElementById('client-phone') || document.querySelector('input[name="client_phone"]');
        if (phoneInput) phoneInput.value = profile.phone;
    }
    
    // Заполняем скрытое поле telegram_id
    if (profile.telegram_id) {
        const telegramIdInput = document.querySelector('input[name="telegram_id"]');
        if (telegramIdInput) telegramIdInput.value = profile.telegram_id;
    }
    
    // Если есть последний барбер, можно предзаполнить его
    if (profile.last_barber_code) {
        const barberCodeInput = document.querySelector('input[name="barber_code"]');
        if (barberCodeInput) barberCodeInput.value = profile.last_barber_code;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing Telegram integration...');
    
    // Если есть форма создания записи, заполняем её данными профиля
    fillAppointmentFormWithProfile();
    
    // Обработчик для сохранения профиля
    const saveProfileBtn = document.getElementById('save-profile-btn');
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', function() {
            const profileData = {
                telegram_id: localStorage.getItem('telegram_user_id') || '',
                first_name: document.getElementById('first-name')?.value || '',
                last_name: document.getElementById('last-name')?.value || '',
                phone: document.getElementById('phone')?.value || ''
            };
            
            saveUserProfile(profileData);
        });
    }
    
    // Добавляем обработчик для формы создания записи
    const appointmentForm = document.getElementById('appointment-form');
    if (appointmentForm) {
        appointmentForm.addEventListener('submit', function(e) {
            // Добавляем telegram_id в данные формы
            const telegramId = localStorage.getItem('telegram_user_id');
            if (telegramId) {
                const telegramIdInput = document.createElement('input');
                telegramIdInput.type = 'hidden';
                telegramIdInput.name = 'telegram_id';
                telegramIdInput.value = telegramId;
                this.appendChild(telegramIdInput);
            }
        });
    }
});
