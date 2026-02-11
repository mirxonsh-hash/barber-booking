// js/api.js - ПОЛНЫЙ API для Render сервера
const BarberSystem = {
    baseURL: 'https://barber-booking-db.onrender.com',

    // ================= Авторизация барбера =================
    loginBarber: async function (username, password) {
        try {
            const response = await fetch(`${this.baseURL}/api/barber/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: username, password: password })
            });

            const data = await response.json();

            if (data.success && data.token) {
                localStorage.setItem('barber_token', data.token);
                localStorage.setItem('barber_code', data.barber?.code || username);
                localStorage.setItem('barber_name', data.barber?.name || 'Барбер');

                return { success: true, barber: data.barber, token: data.token };
            } else {
                return { success: false, error: data.error || 'Ошибка входа' };
            }
        } catch (e) {
            console.error('Ошибка входа:', e);
            return { success: false, error: 'Ошибка соединения с сервером' };
        }
    },

    // ================= Проверка авторизации (ПОЧИНЕНО) =================
    checkAuth: async function () {
        let token = localStorage.getItem('barber_token');

        // если нет в localStorage — берём из URL
        if (!token) {
            const params = new URLSearchParams(window.location.search);
            const urlToken = params.get('token');
            if (urlToken) {
                token = urlToken;
                localStorage.setItem('barber_token', token);
            }
        }

        if (!token) return { authenticated: false };

        try {
            const response = await fetch(`${this.baseURL}/api/barber/check`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.authenticated) {
                return data;
            } else {
                localStorage.removeItem('barber_token');
                localStorage.removeItem('barber_code');
                localStorage.removeItem('barber_name');
                return { authenticated: false };
            }
        } catch (e) {
            console.error('Ошибка проверки барбера:', e);
            return { authenticated: false };
        }
    },

    // ================= Записи барбера =================
    getBarberAppointments: async function () {
        const token = localStorage.getItem('barber_token');
        if (!token) return { success: false, error: "Требуется авторизация" };

        try {
            const response = await fetch(`${this.baseURL}/api/barber/appointments`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();
            return data;
        } catch (e) {
            console.error('Ошибка загрузки записей:', e);
            return { success: false, error: "Ошибка соединения с сервером" };
        }
    },

    // ================= Выход =================
    logout: function () {
        localStorage.removeItem('barber_token');
        localStorage.removeItem('barber_code');
        localStorage.removeItem('barber_name');
        window.location.href = '/barber-login.html';
    }
};

// Экспорт
window.BarberSystem = BarberSystem;
