import os

# Содержимое для profile.html (который я дал с аватаркой)
profile_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iWant - Профиль мастера</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            width: 100%;
            max-width: 400px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .header {
            background: linear-gradient(to right, #1a1a1a, #2d2d2d);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        
        .back-btn {
            position: absolute;
            top: 20px;
            left: 20px;
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
        }
        
        .avatar-container {
            margin: 20px auto;
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            color: white;
            border: 5px solid white;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .avatar-letter {
            font-weight: bold;
            font-size: 48px;
        }
        
        .master-name {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .master-code {
            color: #ccc;
            font-size: 16px;
            margin-bottom: 10px;
        }
        
        .rating {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            margin-top: 10px;
        }
        
        .star {
            color: gold;
        }
        
        .info-section {
            padding: 30px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 15px 0;
            border-bottom: 1px solid #eee;
        }
        
        .info-label {
            color: #666;
        }
        
        .info-value {
            font-weight: bold;
            color: #333;
        }
        
        .action-btn {
            display: block;
            width: 100%;
            margin-top: 30px;
            padding: 18px;
            background: linear-gradient(to right, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }
        
        .action-btn i {
            font-size: 20px;
        }
        
        .page {
            transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .page.slide-out {
            transform: translateX(-100%);
        }
        
        .page.slide-in {
            transform: translateX(0);
        }
        
        .hidden {
            display: none;
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container page" id="profilePage">
        <div class="header">
            <button class="back-btn" onclick="goBack()">
                <i class="fas fa-arrow-left"></i>
            </button>
            <h1 style="margin-bottom: 10px;">Ваш мастер</h1>
            <p>Запись к профессиональному барберу</p>
        </div>
        
        <div class="avatar-container" id="avatar">
            <span class="avatar-letter" id="avatarLetter">А</span>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <div class="master-name" id="masterName">Александр Барбер</div>
            <div class="master-code" id="masterCode">Код: B-ARBER003</div>
            <div class="rating">
                <i class="fas fa-star star"></i>
                <i class="fas fa-star star"></i>
                <i class="fas fa-star star"></i>
                <i class="fas fa-star star"></i>
                <i class="fas fa-star-half-alt star"></i>
                <span style="margin-left: 5px;">4.8 (124 отзыва)</span>
            </div>
        </div>
        
        <div class="info-section">
            <div class="info-item">
                <span class="info-label">Стаж работы</span>
                <span class="info-value">7 лет</span>
            </div>
            <div class="info-item">
                <span class="info-label">Специализация</span>
                <span class="info-value">Мужские стрижки, Бритьё</span>
            </div>
            <div class="info-item">
                <span class="info-label">Среднее время</span>
                <span class="info-value">45 минут</span>
            </div>
            <div class="info-item">
                <span class="info-label">Работает с</span>
                <span class="info-value">2016 года</span>
            </div>
            
            <button class="action-btn" onclick="openSchedulePage()">
                <i class="fas fa-calendar-alt"></i> Выбрать время записи
            </button>
        </div>
    </div>
    
    <div class="container page hidden" id="schedulePage">
        <div class="header">
            <button class="back-btn" onclick="goToProfile()">
                <i class="fas fa-arrow-left"></i>
            </button>
            <h1>Выберите время</h1>
            <p>Запись к <span id="scheduleMasterName">Александру</span></p>
        </div>
        
        <div style="padding: 30px;">
            <div style="text-align: center; margin: 30px 0;">
                <div style="position: relative; width: 200px; height: 200px; margin: 0 auto;">
                    <svg width="200" height="200" viewBox="0 0 200 200">
                        <circle cx="100" cy="100" r="90" fill="none" stroke="#f0f0f0" stroke-width="20"/>
                        <circle cx="100" cy="100" r="90" fill="none" stroke="#667eea" stroke-width="20"
                                stroke-dasharray="565.48" stroke-dashoffset="508.93"
                                stroke-linecap="round" transform="rotate(-90 100 100)"/>
                        <text x="100" y="95" text-anchor="middle" font-size="32" font-weight="bold" fill="#333">10%</text>
                        <text x="100" y="125" text-anchor="middle" font-size="14" fill="#666">заполнено</text>
                    </svg>
                    
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
                        <div style="font-size: 14px; color: #666;">Доступно</div>
                        <div style="font-size: 24px; font-weight: bold; color: #333;">18:30</div>
                        <div style="font-size: 12px; color: #888;">из 20 часов</div>
                    </div>
                </div>
                
                <div style="margin-top: 30px;">
                    <h3>Статистика загрузки</h3>
                    <div style="display: flex; justify-content: center; gap: 30px; margin-top: 20px;">
                        <div style="text-align: center;">
                            <div style="font-size: 32px; font-weight: bold; color: #667eea;">1.5%</div>
                            <div style="font-size: 14px; color: #666;">Отмен</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 32px; font-weight: bold; color: #28a745;">98.5%</div>
                            <div style="font-size: 14px; color: #666">Выполнено</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <h3 style="margin-bottom: 20px;">Ближайшие свободные даты</h3>
                <div id="availableDates">
                    <div style="text-align: center; padding: 30px; color: #666;">
                        Загрузка расписания...
                    </div>
                </div>
            </div>
            
            <button class="action-btn" onclick="confirmBooking()" style="margin-top: 30px;">
                <i class="fas fa-check-circle"></i> Подтвердить выбор
            </button>
        </div>
    </div>

    <script>
        // Получаем код мастера из URL
        const urlParams = new URLSearchParams(window.location.search);
        const masterCode = urlParams.get('code') || 'B-ARBER003';
        
        document.getElementById('masterCode').textContent = `Код: ${masterCode}`;
        
        // Берем первую букву имени для аватарки
        const masterName = "Александр";
        document.getElementById('avatarLetter').textContent = masterName.charAt(0);
        document.getElementById('masterName').textContent = masterName;
        document.getElementById('scheduleMasterName').textContent = masterName;
        
        function goBack() {
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.close();
            } else {
                window.location.href = '/';
            }
        }
        
        function openSchedulePage() {
            const profilePage = document.getElementById('profilePage');
            const schedulePage = document.getElementById('schedulePage');
            
            profilePage.classList.add('slide-out');
            
            setTimeout(() => {
                profilePage.classList.add('hidden');
                schedulePage.classList.remove('hidden');
                schedulePage.classList.add('slide-in');
                
                loadSchedule();
            }, 300);
        }
        
        function goToProfile() {
            const profilePage = document.getElementById('profilePage');
            const schedulePage = document.getElementById('schedulePage');
            
            schedulePage.classList.remove('slide-in');
            schedulePage.classList.add('slide-out');
            
            setTimeout(() => {
                schedulePage.classList.add('hidden');
                profilePage.classList.remove('hidden');
                profilePage.classList.remove('slide-out');
            }, 300);
        }
        
        function loadSchedule() {
            const availableDates = document.getElementById('availableDates');
            
            const dates = [
                { date: '2024-12-15', day: 'Сегодня', times: ['14:00', '15:30', '17:00', '18:30'] },
                { date: '2024-12-16', day: 'Завтра', times: ['10:00', '11:30', '13:00', '14:30'] },
                { date: '2024-12-17', day: 'Вт', times: ['12:00', '13:30', '15:00', '16:30'] }
            ];
            
            let html = '';
            dates.forEach(dateInfo => {
                html += `
                    <div style="background: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 15px;">
                        <div style="font-weight: bold; margin-bottom: 10px;">${dateInfo.day}</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                `;
                
                dateInfo.times.forEach(time => {
                    html += `
                        <button style="padding: 8px 15px; background: white; border: 2px solid #667eea; 
                                border-radius: 8px; color: #667eea; font-weight: bold; cursor: pointer;"
                                onclick="selectTime('${dateInfo.date}', '${time}')">
                            ${time}
                        </button>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            });
            
            availableDates.innerHTML = html;
        }
        
        let selectedDate = null;
        let selectedTime = null;
        
        function selectTime(date, time) {
            selectedDate = date;
            selectedTime = time;
            
            document.querySelectorAll('#availableDates button').forEach(btn => {
                btn.style.background = 'white';
                btn.style.color = '#667eea';
            });
            
            event.target.style.background = '#667eea';
            event.target.style.color = 'white';
        }
        
        function confirmBooking() {
            if (!selectedDate || !selectedTime) {
                alert('Пожалуйста, выберите время!');
                return;
            }
            
            alert(`✅ Запись подтверждена!\\n\\nДата: ${selectedDate}\\nВремя: ${selectedTime}\\nМастер: ${masterName}`);
        }
    </script>
</body>
</html>'''

# Содержимое для index.html
index_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iWant | Премиум запись</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        }

        body {
            background: #f8f9fa;
            color: #333;
            line-height: 1.5;
        }

        .app-container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            box-shadow: 0 0 40px rgba(0,0,0,0.05);
        }

        .header {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }

        .logo {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        .logo span {
            color: #888;
            font-weight: 300;
        }

        .subtitle {
            font-size: 14px;
            color: #aaa;
            margin-top: 5px;
        }

        .content {
            padding: 30px 25px;
        }

        .section {
            margin-bottom: 35px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #222;
            display: flex;
            align-items: center;
        }

        .section-title i {
            margin-right: 12px;
            color: #444;
        }

        .code-input-container {
            background: #f5f5f5;
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid #eee;
        }

        .input-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
            display: block;
        }

        .code-input {
            width: 100%;
            padding: 18px 20px;
            font-size: 20px;
            letter-spacing: 3px;
            font-weight: 600;
            text-align: center;
            border: 2px solid #ddd;
            border-radius: 12px;
            background: white;
            color: #222;
            text-transform: uppercase;
        }

        .code-example {
            font-size: 13px;
            color: #888;
            margin-top: 12px;
            text-align: center;
        }

        .btn-primary {
            display: block;
            width: 100%;
            padding: 18px;
            background: linear-gradient(to right, #222, #444);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
        }

        .btn-primary i {
            margin-right: 10px;
        }

        .divider {
            display: flex;
            align-items: center;
            margin: 30px 0;
            color: #999;
        }

        .divider::before,
        .divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #e0e0e0;
        }

        .divider-text {
            padding: 0 15px;
            font-size: 13px;
            text-transform: uppercase;
        }

        .master-panel {
            background: #f9f9f9;
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            border: 1px solid #eee;
            cursor: pointer;
        }

        .master-icon {
            font-size: 32px;
            color: #444;
            margin-bottom: 15px;
        }

        .master-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #222;
        }

        .master-desc {
            font-size: 14px;
            color: #777;
        }

        .footer {
            padding: 25px;
            text-align: center;
            background: #f8f8f8;
            border-top: 1px solid #eee;
            color: #888;
            font-size: 13px;
        }

        .footer-links {
            display: flex;
            justify-content: center;
            gap: 25px;
            margin-bottom: 15px;
        }

        .footer-link {
            color: #666;
            text-decoration: none;
        }

        .copyright {
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header class="header">
            <div class="logo">i<span>Want</span></div>
            <div class="subtitle">Премиум сервис записи к мастеру</div>
        </header>

        <main class="content">
            <div class="section">
                <h1 class="section-title">
                    <i class="fas fa-crown"></i> Премиум запись к мастеру
                </h1>
                <p style="color: #777; margin-bottom: 25px; font-size: 15px;">
                    Введите код мастера для записи в удобное время
                </p>
            </div>

            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-user-tie"></i> Код мастера
                </h2>
                <div class="code-input-container">
                    <label class="input-label">Получите код у своего мастера и введите его ниже</label>
                    <input type="text" class="code-input" id="masterCode" placeholder="B-ABC123" maxlength="10">
                    <div class="code-example">Пример: B-ABC123</div>
                </div>
                
                <button class="btn-primary" id="continueBtn">
                    <i class="fas fa-arrow-right"></i> Продолжить →
                </button>
            </div>

            <div class="divider">
                <span class="divider-text">или</span>
            </div>

            <div class="section">
                <h2 class="section-title">
                    <i class="fas fa-sliders-h"></i> Я мастер
                </h2>
                <div class="master-panel" id="masterPanel">
                    <div class="master-icon">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h3 class="master-title">Панель управления записями</h3>
                    <p class="master-desc">
                        Войдите в систему для управления расписанием, 
                        клиентами и статистикой
                    </p>
                </div>
            </div>
        </main>

        <footer class="footer">
            <div class="footer-links">
                <a href="#" class="footer-link">Поддержка</a>
                <a href="#" class="footer-link">Инструкция</a>
                <a href="#" class="footer-link">О сервисе</a>
            </div>
            <div class="copyright">
                © 2024 iWant. Премиум сервис записи
            </div>
        </footer>
    </div>

    <script>
        const masterPanel = document.getElementById('masterPanel');
        const continueBtn = document.getElementById('continueBtn');
        const masterCodeInput = document.getElementById('masterCode');

        // Мастер панель
        masterPanel.addEventListener('click', () => {
            window.location.href = '/master-login';
        });

        // Продолжить
        continueBtn.addEventListener('click', () => {
            const code = masterCodeInput.value.trim().toUpperCase();
            
            if (!code) {
                alert('Введите код мастера');
                masterCodeInput.focus();
                return;
            }
            
            // Переход на профиль с кодом
            window.location.href = `/profile?code=${code}`;
        });

        // Автоформат кода
        masterCodeInput.addEventListener('input', function(e) {
            let value = e.target.value.toUpperCase();
            value = value.replace(/[^A-Z0-9\-]/g, '');
            e.target.value = value;
        });

        // Enter для отправки
        masterCodeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                continueBtn.click();
            }
        });
    </script>
</body>
</html>'''

# Содержимое для других файлов (упрощённое)
master_login_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iWant - Вход для мастера</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        
        .logo {
            text-align: center;
            color: #667eea;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        
        .btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            text-align: center;
            text-decoration: none;
            display: block;
        }
        
        .btn-cancel {
            background: #f0f0f0;
            color: #333;
        }
        
        .btn-login {
            background: #667eea;
            color: white;
        }
        
        .support-links {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        
        .support-links a {
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #777;
            font-size: 12px;
        }
        
        .error-message {
            color: #ff4757;
            background: #ffeaea;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">iWant</div>
        <div class="subtitle">Панель управления</div>
        
        <div id="errorMessage" class="error-message"></div>
        
        <div class="form-group">
            <label for="username">Логин (код мастера)</label>
            <input type="text" id="username" placeholder="B-ABC123">
        </div>
        
        <div class="form-group">
            <label for="password">Пароль</label>
            <input type="password" id="password" placeholder="Введите пароль">
        </div>
        
        <div class="btn-group">
            <a href="/" class="btn btn-cancel">Отмена</a>
            <button onclick="login()" class="btn btn-login">Войти</button>
        </div>
        
        <div class="support-links">
            <a href="#">Поддержка</a>
            <a href="#">Инструкция</a>
            <a href="#">Сервис</a>
        </div>
        
        <div class="footer">
            © 2024 iWant. Премиум сервис записи
        </div>
    </div>

    <script>
        function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorElement = document.getElementById('errorMessage');
            
            if (!username || !password) {
                errorElement.textContent = 'Пожалуйста, заполните все поля';
                errorElement.style.display = 'block';
                return;
            }
            
            // Для теста - если ввести B-ARBER003
            if (username === 'B-ARBER003' && password === '123') {
                localStorage.setItem('master', JSON.stringify({
                    id: 1,
                    name: 'Александр',
                    code: 'B-ARBER003'
                }));
                window.location.href = '/master-panel';
            } else {
                errorElement.textContent = 'Неверный код мастера или пароль';
                errorElement.style.display = 'block';
            }
        }
        
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                login();
            }
        });
    </script>
</body>
</html>'''

master_panel_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iWant - Панель управления</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            background: #f5f5f5;
        }
        
        .header {
            background: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            color: #667eea;
            font-size: 24px;
            font-weight: bold;
        }
        
        .master-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .master-name {
            font-weight: bold;
            color: #333;
        }
        
        .logout-btn {
            background: #ff4757;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
        }
        
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .section-title {
            font-size: 20px;
            font-weight: bold;
            margin: 30px 0 15px;
            color: #333;
        }
        
        .code-display {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
            text-align: center;
        }
        
        .code-value {
            font-family: monospace;
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        
        .code-label {
            color: #666;
            font-size: 14px;
        }
        
        .footer {
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #777;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">iWant - Панель управления</div>
        <div class="master-info">
            <span class="master-name" id="masterName"></span>
            <button onclick="logout()" class="logout-btn">Выйти</button>
        </div>
    </div>
    
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="todayAppointments">5</div>
                <div class="stat-label">Сегодня</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="pendingAppointments">3</div>
                <div class="stat-label">Ожидают</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalAppointments">127</div>
                <div class="stat-label">Всего записей</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="completionRate">98%</div>
                <div class="stat-label">Выполнено</div>
            </div>
        </div>
        
        <div class="code-display">
            <div class="code-label">Ваш код для клиентов:</div>
            <div class="code-value" id="masterCode">B-ARBER003</div>
            <div class="code-label">Дайте этот код клиентам для записи</div>
            <div style="margin-top: 10px;">
                <a href="/profile?code=B-ARBER003" style="color: #667eea;">Посмотреть как видят клиенты</a>
            </div>
        </div>
        
        <div class="section-title">Инструкция</div>
        <div style="background: white; padding: 20px; border-radius: 10px;">
            <p>1. Дайте ваш код <strong>B-ARBER003</strong> клиентам</p>
            <p>2. Клиенты вводят код в приложении iWant</p>
            <p>3. Вы видите записи в этой панели</p>
            <p>4. Подтверждайте или отменяйте записи</p>
        </div>
    </div>
    
    <div class="footer">
        <div style="margin-bottom: 10px;">
            <a href="#" style="color: #667eea; margin: 0 10px;">Поддержка</a>
            <a href="#" style="color: #667eea; margin: 0 10px;">Инструкция</a>
            <a href="#" style="color: #667eea; margin: 0 10px;">Сервис</a>
        </div>
        © 2024 iWant. Премиум сервис записи
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const masterData = localStorage.getItem('master');
            
            if (!masterData) {
                window.location.href = '/master-login';
                return;
            }
            
            const master = JSON.parse(masterData);
            document.getElementById('masterName').textContent = master.name;
            document.getElementById('masterCode').textContent = master.code;
        });
        
        function logout() {
            localStorage.removeItem('master');
            window.location.href = '/master-login';
        }
    </script>
</body>
</html>'''

# Записываем файлы
os.makedirs('templates', exist_ok=True)

files = {
    'profile.html': profile_html,
    'index.html': index_html,
    'master_login.html': master_login_html,
    'master_panel.html': master_panel_html
}

for filename, content in files.items():
    filepath = os.path.join('templates', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ Создан файл: {filepath}')

print('\n🎉 Все файлы обновлены!')
print('🚀 Перезапусти сервер: python server.py')
