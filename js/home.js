// static/js/home.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏠 Главная страница iWant загружена');
    
    // Проверяем Telegram Web App
    checkTelegramEnvironment();
    
    // Анимация появления элементов при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    // Наблюдаем за всеми элементами с анимацией
    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });

    // Плавная прокрутка для якорных ссылок
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            if (href === '#') return;
            
            e.preventDefault();
            const targetElement = document.querySelector(href);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Анимация для плавающих карточек
    const floatingCards = document.querySelectorAll('.floating-card');
    floatingCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.5}s`;
    });

    // Динамическое изменение шапки при скролле
    const header = document.querySelector('.header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header.style.boxShadow = '0 5px 20px rgba(0,0,0,0.1)';
            header.style.background = 'rgba(255,255,255,0.95)';
            header.style.backdropFilter = 'blur(10px)';
        } else {
            header.style.boxShadow = 'var(--shadow-light)';
            header.style.background = 'white';
            header.style.backdropFilter = 'none';
        }
        
        lastScroll = currentScroll;
    });

    // Анимация для статистики
    const statNumbers = document.querySelectorAll('.stat-number');
    const statSection = document.querySelector('.hero-stats');
    
    const statObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                statNumbers.forEach(stat => {
                    const finalValue = stat.textContent;
                    stat.textContent = '0';
                    
                    let counter = 0;
                    const increment = parseInt(finalValue) / 50;
                    
                    const timer = setInterval(() => {
                        counter += increment;
                        stat.textContent = Math.floor(counter);
                        
                        if (counter >= parseInt(finalValue)) {
                            stat.textContent = finalValue;
                            clearInterval(timer);
                        }
                    }, 30);
                });
                
                statObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    if (statSection) {
        statObserver.observe(statSection);
    }
    
    // Проверка сессии при загрузке
    checkClientSession();
});

// Проверка окружения Telegram
function checkTelegramEnvironment() {
    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
        console.log('✅ Работаем в Telegram Web App');
        
        const tg = Telegram.WebApp;
        
        // Настраиваем тему
        tg.setHeaderColor('#4a6fa5');
        tg.setBackgroundColor('#0a0a0a');
        
        // Показываем главную кнопку
        tg.MainButton.setText('Начать запись');
        tg.MainButton.show();
        tg.MainButton.onClick(() => {
            handleClientClick();
        });
        
    } else {
        console.log('🌐 Работаем в обычном браузере');
    }
}

// Проверка сессии клиента
function checkClientSession() {
    const clientToken = localStorage.getItem('clientToken');
    
    if (clientToken) {
        console.log('🔑 Найдена сессия клиента');
        
        // Проверяем валидность токена
        fetch('https://barber-booking-db.onrender.com/api/client/session', {
            headers: {
                'Authorization': `Bearer ${clientToken}`
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                console.log('✅ Сессия активна для:', data.client.phone);
                
                // Обновляем кнопку "Я клиент"
                const clientBtn = document.querySelector('.btn-primary');
                if (clientBtn) {
                    clientBtn.innerHTML = '<i class="fas fa-calendar-check"></i> Записаться';
                    clientBtn.onclick = function() {
                        window.location.href = '/client-login';
                    };
                }
            } else {
                console.log('❌ Сессия истекла, очищаем');
                localStorage.removeItem('clientToken');
                localStorage.removeItem('clientPhone');
            }
        })
        .catch(error => {
            console.error('❌ Ошибка проверки сессии:', error);
        });
    }
}

// Обработка клика "Я клиент"
function handleClientClick() {
    const clientToken = localStorage.getItem('clientToken');
    
    if (clientToken) {
        // Уже зарегистрирован - переходим к поиску барбера
        window.location.href = '/client-login';
    } else {
        // Показываем окно регистрации
        if (typeof openRegistrationModal === 'function') {
            openRegistrationModal();
        } else {
            // Если функция не определена, переходим на страницу входа
            window.location.href = '/client-login';
        }
    }
}

// Функция для форматирования телефона
function formatPhoneNumber(phone) {
    const cleaned = phone.replace(/\D/g, '');
    
    if (cleaned.startsWith('998')) {
        const match = cleaned.match(/^998(\d{2})(\d{3})(\d{2})(\d{2})$/);
        if (match) {
            return `+998 ${match[1]} ${match[2]} ${match[3]} ${match[4]}`;
        }
    }
    
    return phone;
}

// Глобальные функции для доступа из HTML
window.handleClientClick = handleClientClick;
window.formatPhoneNumber = formatPhoneNumber;
