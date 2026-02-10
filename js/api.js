// js/api.js - ПОЛНЫЙ API для Render сервера
const BarberSystem = {
    baseURL: 'https://barber-booking-db.onrender.com',
    
    // Авторизация барбера
    loginBarber: async function(username, password) {
        try {
            const response = await fetch(`${this.baseURL}/api/barber/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code: username,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.token) {
                localStorage.setItem('barberToken', data.token);
                localStorage.setItem('barberData', JSON.stringify(data.barber));
                
                return {
                    success: true,
                    message: "Успешный вход",
                    barber: data.barber,
                    token: data.token
                };
            } else {
                return {
                    success: false,
                    error: data.error || "Ошибка входа"
                };
            }
        } catch (error) {
            console.error('Ошибка входа:', error);
            return {
                success: false,
                error: "Ошибка соединения с сервером"
            };
        }
    },

    // Проверка авторизации
    checkAuth: async function() {
        const token = localStorage.getItem('barberToken');
        if (!token) {
            return { authenticated: false };
        }
        
        try {
            const response = await fetch(`${this.baseURL}/api/barber/check`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Ошибка проверки авторизации:', error);
            return { authenticated: false };
        }
    },

    // Получить записи барбера
    getBarberAppointments: async function() {
        const token = localStorage.getItem('barberToken');
        if (!token) {
            return { success: false, error: "Требуется авторизация" };
        }
        
        try {
            const response = await fetch(`${this.baseURL}/api/barber/appointments`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            const data = await response.json();
            
            if (data.success && data.appointments) {
                return {
                    success: true,
                    appointments: data.appointments,
                    count: data.count || data.appointments.length
                };
            } else {
                return {
                    success: false,
                    error: data.error || "Ошибка загрузки записей"
                };
            }
        } catch (error) {
            console.error('Ошибка загрузки записей:', error);
            return {
                success: false,
                error: "Ошибка соединения с сервером"
            };
        }
    },

    // Проверка кода мастера (для клиентов)
    checkMasterCode: async function(code) {
        try {
            const response = await fetch(`${this.baseURL}/api/barber/${code}`);
            const data = await response.json();
            
            if (data.success && data.barber) {
                return {
                    success: true,
                    message: "Мастер найден",
                    master: data.barber
                };
            } else {
                return {
                    success: false,
                    error: data.error || "Мастер с таким кодом не найден"
                };
            }
        } catch (error) {
            console.error('Ошибка проверки кода:', error);
            return {
                success: false,
                error: "Ошибка соединения с сервером"
            };
        }
    },

    // Получить услуги мастера
    getMasterServices: async function(code) {
        try {
            const response = await fetch(`${this.baseURL}/api/barber/${code}/services`);
            const services = await response.json();
            
            return {
                success: true,
                services: services
            };
        } catch (error) {
            console.error('Ошибка загрузки услуг:', error);
            return {
                success: true,
                services: [
                    { id: 1, name: 'Мужская стрижка', price: 1500, duration: 45 },
                    { id: 2, name: 'Стрижка + Бритьё', price: 2000, duration: 60 },
                    { id: 3, name: 'Королевское бритьё', price: 800, duration: 30 }
                ]
            };
        }
    },

    // Создать запись (клиент)
    createBooking: async function(bookingData) {
        try {
            console.log('📤 Отправка записи на сервер:', bookingData);
            
            const response = await fetch(`${this.baseURL}/api/appointments/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(bookingData)
            });
            
            const data = await response.json();
            console.log('📥 Ответ сервера:', data);
            
            if (data.success) {
                // Сохраняем локально
                const localBookings = JSON.parse(localStorage.getItem('barberBookings') || '[]');
                localBookings.push({
                    id: data.appointment_id,
                    ...bookingData,
                    status: 'active',
                    created: new Date().toISOString()
                });
                localStorage.setItem('barberBookings', JSON.stringify(localBookings));
                
                return {
                    success: true,
                    message: data.message || "Запись успешно создана!",
                    booking: data.appointment || bookingData,
                    appointment_id: data.appointment_id
                };
            } else {
                console.error('❌ Ошибка сервера:', data.error);
                return {
                    success: false,
                    error: data.error || "Ошибка создания записи"
                };
            }
        } catch (error) {
            console.error('❌ Ошибка сети:', error);
            return {
                success: false,
                error: "Ошибка соединения с сервером"
            };
        }
    },

    // Обновить статус записи (барбер)
    updateBookingStatus: async function(bookingId, status) {
        const token = localStorage.getItem('barberToken');
        if (!token) {
            return { success: false, error: "Требуется авторизация" };
        }
        
        try {
            // Пока просто локально, можно добавить API endpoint позже
            const localBookings = JSON.parse(localStorage.getItem('barberBookings') || '[]');
            const booking = localBookings.find(b => b.id == bookingId);
            
            if (booking) {
                booking.status = status;
                booking.updated = new Date().toISOString();
                localStorage.setItem('barberBookings', JSON.stringify(localBookings));
                
                return {
                    success: true,
                    message: "Статус обновлен",
                    booking: booking
                };
            }
            
            return {
                success: false,
                error: "Запись не найдена"
            };
        } catch (error) {
            console.error('Ошибка обновления:', error);
            return {
                success: false,
                error: "Ошибка обновления статуса"
            };
        }
    },

    // Выход из системы
    logout: function() {
        localStorage.removeItem('barberToken');
        localStorage.removeItem('barberData');
        localStorage.removeItem('barberBookings');
        window.location.href = '/barber-login'; // ИЗМЕНЕНО: убрали .html
    },

    // Получить текущего барбера
    getCurrentBarber: function() {
        const barberData = localStorage.getItem('barberData');
        return barberData ? JSON.parse(barberData) : null;
    },

    // Получить статистику
    getBarberStats: function() {
        const localBookings = JSON.parse(localStorage.getItem('barberBookings') || '[]');
        const currentBarber = this.getCurrentBarber();
        
        if (!currentBarber) {
            return { total: 0, completed: 0, pending: 0, cancelled: 0, completionRate: 0 };
        }
        
        const barberBookings = localBookings.filter(b => b.barber_code === currentBarber.code);
        const completed = barberBookings.filter(b => b.status === 'completed').length;
        const pending = barberBookings.filter(b => b.status === 'active' || b.status === 'pending').length;
        const cancelled = barberBookings.filter(b => b.status === 'cancelled').length;
        
        return {
            total: barberBookings.length,
            completed: completed,
            pending: pending,
            cancelled: cancelled,
            completionRate: barberBookings.length > 0 ? 
                Math.round((completed / barberBookings.length) * 100) : 0
        };
    },

    // Проверить доступность сервера
    checkServerStatus: async function() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/all-appointments`);
            return response.ok;
        } catch (error) {
            console.error('Сервер недоступен:', error);
            return false;
        }
    },

    // Получить все записи (для отладки)
    getAllAppointments: async function() {
        try {
            const response = await fetch(`${this.baseURL}/api/debug/all-appointments`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Ошибка загрузки всех записей:', error);
            return { success: false, error: "Ошибка загрузки" };
        }
    }
};

// Экспортируем для использования
window.BarberSystem = BarberSystem;

// Авто-проверка при загрузке - ТОЛЬКО ДЛЯ ОТЛАДКИ
// document.addEventListener('DOMContentLoaded', function() {
//     console.log('✅ BarberSystem API загружен');
//     console.log('🔗 Сервер:', BarberSystem.baseURL);
// });
