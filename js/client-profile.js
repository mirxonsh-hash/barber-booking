// Конфигурация
const API_BASE = 'http://localhost:5000'; // Измените на ваш адрес
let userData = null;

// Основные функции
async function initializeProfile() {
    console.log('🚀 Инициализация профиля...');
    
    // 1. Пытаемся загрузить из localStorage
    loadFromLocalStorage();
    
    // 2. Если есть telegram_id, загружаем с сервера
    if (userData && userData.id && userData.id !== 'test_user') {
        await loadUserProfile(userData.id);
    }
    
    // 3. Обновляем интерфейс
    updateProfileUI();
    
    // 4. Загружаем барберов
    await loadBarbers();
}

function loadFromLocalStorage() {
    try {
        const storedData = localStorage.getItem('user_profile');
        if (storedData) {
            userData = JSON.parse(storedData);
            console.log('📱 Данные из localStorage:', userData);
        } else {
            createDefaultUserData();
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки из localStorage:', error);
        createDefaultUserData();
    }
}

function createDefaultUserData() {
    userData = {
        id: 'test_user',
        firstName: 'Тестовый',
        lastName: 'Пользователь',
        username: 'test_user',
        photoUrl: '',
        phone: ''
    };
    localStorage.setItem('user_profile', JSON.stringify(userData));
    console.log('👤 Создан тестовый профиль');
}

async function loadUserProfile(telegramId) {
    try {
        const response = await fetch(`${API_BASE}/api/client/profile?telegram_id=${telegramId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        console.log('📡 Данные с сервера:', data);

        if (data.success && data.profile) {
            userData = {
                id: data.profile.telegram_id || telegramId,
                firstName: data.profile.first_name || 'Пользователь',
                lastName: data.profile.last_name || '',
                username: data.profile.username || '',
                photoUrl: data.profile.photo_url || '',
                phone: data.profile.phone || ''
            };
            localStorage.setItem('user_profile', JSON.stringify(userData));
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки профиля:', error);
    }
}

function updateProfileUI() {
    if (!userData) {
        console.warn('⚠️ Нет данных пользователя');
        return;
    }

    // Обновляем имя
    const nameElement = document.getElementById('profileName');
    if (nameElement) {
        nameElement.textContent = `${userData.firstName} ${userData.lastName}`.trim() || 'Пользователь';
    }

    // Обновляем username
    const usernameElement = document.getElementById('profileUsername');
    if (usernameElement) {
        usernameElement.textContent = userData.username ? `@${userData.username}` : '';
    }

    // Обновляем телефон
    const phoneElement = document.getElementById('profilePhone');
    if (phoneElement) {
        phoneElement.textContent = userData.phone || 'Не указан';
    }

    // Обновляем аватар
    updateAvatar();
}

function updateAvatar() {
    if (!userData) return;

    const avatarElement = document.getElementById('profileAvatar');
    const initialElement = document.getElementById('avatarInitials');

    // Проверяем элементы
    if (!avatarElement || !initialElement) {
        console.error('❌ Элементы аватара не найдены');
        return;
    }

    if (userData.photoUrl) {
        avatarElement.style.backgroundImage = `url(${userData.photoUrl})`;
        initialElement.style.display = 'none';
    } else {
        avatarElement.style.backgroundImage = '';
        initialElement.style.display = 'flex';
        const initials = (userData.firstName?.[0] || '') + (userData.lastName?.[0] || '');
        initialElement.textContent = initials || '?';
    }
}

// Функции для работы с барберами
async function loadBarbers() {
    console.log('📋 Загрузка барберов...');
    
    if (!userData || !userData.id) {
        console.warn('👤 Пользователь не авторизован');
        renderBarbers([]);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/client/barbers?client_id=${userData.id}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        console.log('🎯 Ответ сервера по барберам:', data);

        if (data.success) {
            renderBarbers(data.barbers || []);
        } else {
            renderBarbers([]);
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки барберов:', error);
        renderBarbers([]);
    }
}

function renderBarbers(barbers) {
    console.log('🎨 Рендерим барберов:', barbers);
    
    // ВАЖНО: Проверяем существование контейнера
    const container = document.getElementById('barbers-container');
    const noBarbersMessage = document.getElementById('no-barbers-message');
    
    if (!container) {
        console.error('❌ Элемент barbers-container не найден!');
        return;
    }

    // Проверяем, что barbers - массив
    if (!Array.isArray(barbers)) {
        console.warn('⚠️ barbers не является массивом:', barbers);
        barbers = [];
    }

    if (barbers.length === 0) {
        // Показываем сообщение "нет барберов"
        container.style.display = 'none';
        if (noBarbersMessage) {
            noBarbersMessage.style.display = 'block';
        }
        return;
    }

    // Показываем контейнер
    container.style.display = 'block';
    if (noBarbersMessage) {
        noBarbersMessage.style.display = 'none';
    }

    // Генерируем HTML для барберов
    container.innerHTML = barbers.map(barber => `
        <div class="barber-card" data-barber-id="${barber.id}">
            <div class="barber-avatar">
                <div class="barber-avatar-initials">
                    ${(barber.first_name?.[0] || '') + (barber.last_name?.[0] || '')}
                </div>
            </div>
            <div class="barber-info">
                <h4>${barber.first_name || ''} ${barber.last_name || ''}</h4>
                <p>${barber.username ? '@' + barber.username : 'Нет username'}</p>
            </div>
            <button class="btn-remove" onclick="removeBarber(${barber.id})" title="Удалить">
                ✕
            </button>
        </div>
    `).join('');
}

async function addBarber() {
    console.log('➕ Добавление барбера...');
    
    if (!userData || !userData.id) {
        alert('❌ Сначала авторизуйтесь');
        return;
    }

    try {
        // Показываем индикатор загрузки
        const addBtn = document.getElementById('addBarberBtn');
        if (addBtn) {
            addBtn.innerHTML = '⌛ Загрузка...';
            addBtn.disabled = true;
        }

        // 1. Получаем данные из Telegram бота
        const botResponse = await fetch(`${API_BASE}/api/telegram/get-barber?client_id=${userData.id}`);
        if (!botResponse.ok) throw new Error('Ошибка связи с ботом');
        
        const botData = await botResponse.json();
        console.log('🤖 Данные от бота:', botData);

        if (!botData.success) {
            alert('❌ ' + (botData.error || 'Не удалось получить данные барбера'));
            return;
        }

        // 2. Сохраняем барбера на сервере
        const saveResponse = await fetch(`${API_BASE}/api/client/add-barber`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: userData.id,
                barber_telegram_id: botData.barber_id,
                barber_name: botData.first_name + ' ' + botData.last_name,
                barber_username: botData.username
            })
        });

        const saveData = await saveResponse.json();
        console.log('💾 Результат сохранения:', saveData);

        if (saveData.success) {
            alert('✅ Барбер успешно добавлен!');
            // Обновляем список барберов
            await loadBarbers();
        } else {
            alert('❌ ' + (saveData.error || 'Ошибка при сохранении'));
        }

    } catch (error) {
        console.error('🔥 Ошибка при добавлении барбера:', error);
        alert('❌ Произошла ошибка: ' + error.message);
    } finally {
        // Восстанавливаем кнопку
        const addBtn = document.getElementById('addBarberBtn');
        if (addBtn) {
            addBtn.innerHTML = '+ Добавить барбера';
            addBtn.disabled = false;
        }
    }
}

async function removeBarber(barberId) {
    if (!confirm('Удалить этого барбера?')) return;

    try {
        const response = await fetch(`${API_BASE}/api/client/remove-barber`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: userData.id,
                barber_id: barberId
            })
        });

        const data = await response.json();
        
        if (data.success) {
            alert('✅ Барбер удален');
            await loadBarbers();
        } else {
            alert('❌ ' + (data.error || 'Ошибка удаления'));
        }
    } catch (error) {
        console.error('❌ Ошибка удаления барбера:', error);
        alert('❌ Ошибка удаления');
    }
}

// Вспомогательные функции
function editProfile() {
    alert('Редактирование профиля (в разработке)');
}

function editPhone() {
    const newPhone = prompt('Введите номер телефона:', userData?.phone || '');
    if (newPhone !== null) {
        userData.phone = newPhone;
        localStorage.setItem('user_profile', JSON.stringify(userData));
        updateProfileUI();
        
        // Сохраняем на сервере
        savePhoneToServer(newPhone);
    }
}

async function savePhoneToServer(phone) {
    try {
        await fetch(`${API_BASE}/api/client/update-phone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: userData.id,
                phone: phone
            })
        });
    } catch (error) {
        console.error('❌ Ошибка сохранения телефона:', error);
    }
}

function openTelegramBot() {
    window.open('https://t.me/iWantClient_bot', '_blank');
}

function closeModal() {
    const modal = document.getElementById('addBarberModal');
    if (modal) modal.style.display = 'none';
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM загружен');
    initializeProfile();
});
