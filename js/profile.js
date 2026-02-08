// Инициализация Telegram Web App
function initTelegramApp() {
    if (window.Telegram && Telegram.WebApp) {
        console.log('📱 Telegram Web App обнаружен');
        
        Telegram.WebApp.expand();
        Telegram.WebApp.ready();
        
        const user = Telegram.WebApp.initDataUnsafe.user;
        if (user) {
            console.log('👤 Пользователь Telegram:', user.first_name);
            localStorage.setItem('telegram_user_id', user.id);
        }
    } else {
        console.log('🌐 Не в Telegram Web App');
    }
}

// Функция отображения списка барберов
function renderBarbers(barbers) {
    const barberList = document.getElementById('barber-list');
    if (!barberList) {
        console.error('❌ Элемент #barber-list не найден');
        return;
    }
    
    barberList.innerHTML = '';
    
    if (!barbers || barbers.length === 0) {
        barberList.innerHTML = '<p class="no-barbers">Нет добавленных барберов</p>';
        return;
    }
    
    barbers.forEach(barber => {
        const barberElement = document.createElement('div');
        barberElement.className = 'barber-item';
        barberElement.innerHTML = `
            <div class="barber-info">
                <h3>${barber.name || 'Барбер'} (${barber.code})</h3>
                <p>Код: ${barber.code}</p>
            </div>
            <button class="btn btn-primary" onclick="selectBarber('${barber.code}')">
                Выбрать
            </button>
        `;
        barberList.appendChild(barberElement);
    });
}

// Функция добавления барбера
function addBarber() {
    const barberCode = document.getElementById('barber-code').value.trim();
    const barberName = document.getElementById('barber-name').value.trim();
    
    if (!barberCode) {
        alert('Пожалуйста, введите код барбера');
        return;
    }
    
    console.log(`➕ Добавление барбера: ${barberCode} (${barberName || 'без имени'})`);
    
    // Проверяем существование барбера через API
    fetch(`/api/barber/${barberCode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const savedBarbers = JSON.parse(localStorage.getItem('saved_barbers') || '[]');
                
                const existingBarber = savedBarbers.find(b => b.code === barberCode);
                if (existingBarber) {
                    alert('Барбер с таким кодом уже добавлен');
                    return;
                }
                
                savedBarbers.push({
                    code: barberCode,
                    name: barberName || data.barber.name || barberCode,
                    added_at: new Date().toISOString()
                });
                
                localStorage.setItem('saved_barbers', JSON.stringify(savedBarbers));
                renderBarbers(savedBarbers);
                
                document.getElementById('barber-code').value = '';
                document.getElementById('barber-name').value = '';
                
                closeAddBarberModal();
                
                alert('✅ Барбер успешно добавлен!');
            } else {
                alert('❌ Барбер с таким кодом не найден. Проверьте правильность кода.');
            }
        })
        .catch(error => {
            console.error('❌ Ошибка проверки барбера:', error);
            alert('Ошибка проверки барбера. Попробуйте снова.');
        });
}

// Функция выбора барбера
function selectBarber(barberCode) {
    console.log(`🎯 Выбран барбер: ${barberCode}`);
    localStorage.setItem('selected_barber_code', barberCode);
    window.location.href = `/client-panel?code=${barberCode}`;
}

// Загрузка данных при запуске
function loadData() {
    console.log('🚀 Загружаем данные...');
    const savedBarbers = JSON.parse(localStorage.getItem('saved_barbers') || '[]');
    console.log('📱 Данные из localStorage:', savedBarbers);
    
    renderBarbers(savedBarbers);
}

// Открытие модального окна
function openAddBarberModal() {
    const modal = document.getElementById('add-barber-modal');
    if (modal) {
        modal.style.display = 'block';
    }
}

// Закрытие модального окна
function closeAddBarberModal() {
    const modal = document.getElementById('add-barber-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 Страница выбора барбера загружена');
    
    initTelegramApp();
    loadData();
    
    document.getElementById('add-barber-btn')?.addEventListener('click', openAddBarberModal);
    document.getElementById('close-modal')?.addEventListener('click', closeAddBarberModal);
    document.getElementById('barber-add-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        addBarber();
    });
    
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('add-barber-modal');
        if (modal && event.target === modal) {
            modal.style.display = 'none';
        }
    });
});
