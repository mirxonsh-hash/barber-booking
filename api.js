// js/api.js - Mock API для GitHub Pages
const BarberSystem = {
    // Барберы в системе (логины и пароли)
    barbers: [
        {
            id: 1,
            username: "barber",
            password: "123456",
            name: "Александр",
            phone: "+7 999 123-45-67",
            code: "B-ARBER003",
            rating: 4.8,
            reviews: 124,
            experience: "7 лет",
            specialization: "Мужские стрижки, Бритьё",
            avgTime: "45 минут",
            since: "2016",
            email: "barber@example.com"
        },
        {
            id: 2,
            username: "ivan",
            password: "654321",
            name: "Иван Иванов",
            phone: "+7 999 987-65-43",
            code: "IVAN123",
            rating: 4.6,
            reviews: 89,
            experience: "5 лет",
            specialization: "Детские стрижки, Стрижка машинкой",
            avgTime: "30 минут",
            since: "2018",
            email: "ivan@example.com"
        }
    ],

    // Записи (appointments)
    bookings: [],

    // Расписание
    schedule: {
        "B-ARBER003": [
            { 
                date: new Date().toISOString().split('T')[0], 
                day: "Сегодня", 
                times: ["10:00", "11:00", "14:00", "15:00", "17:00"] 
            },
            { 
                date: new Date(Date.now() + 86400000).toISOString().split('T')[0], 
                day: "Завтра", 
                times: ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"] 
            },
            { 
                date: new Date(Date.now() + 172800000).toISOString().split('T')[0], 
                day: "Ср", 
                times: ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"] 
            }
        ],
        "IVAN123": [
            { 
                date: new Date().toISOString().split('T')[0], 
                day: "Сегодня", 
                times: ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"] 
            }
        ]
    },

    // Инициализация
    init: function() {
        // Загружаем данные из localStorage
        const savedBookings = localStorage.getItem('barberBookings');
        if (savedBookings) {
            this.bookings = JSON.parse(savedBookings);
        }
        
        // Инициализируем сессию
        const session = localStorage.getItem('barberSession');
        if (session) {
            this.session = JSON.parse(session);
        }
    },

    // Авторизация барбера
    loginBarber: async function(username, password) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const barber = this.barbers.find(b => 
                    b.username === username && b.password === password
                );
                
                if (barber) {
                    // Создаем сессию
                    this.session = {
                        barberId: barber.id,
                        username: barber.username,
                        name: barber.name,
                        code: barber.code,
                        loggedIn: true,
                        loginTime: new Date().toISOString()
                    };
                    
                    // Сохраняем сессию
                    localStorage.setItem('barberSession', JSON.stringify(this.session));
                    
                    resolve({
                        success: true,
                        message: "Успешный вход",
                        barber: barber
                    });
                } else {
                    resolve({
                        success: false,
                        error: "Неверный логин или пароль"
                    });
                }
            }, 500);
        });
    },

    // Выход из системы
    logout: function() {
        this.session = null;
        localStorage.removeItem('barberSession');
    },

    // Проверка авторизации
    isAuthenticated: function() {
        return this.session && this.session.loggedIn;
    },

    // Получить текущего барбера
    getCurrentBarber: function() {
        if (!this.session) return null;
        return this.barbers.find(b => b.id === this.session.barberId);
    },

    // Проверка кода мастера (для клиентов)
    checkMasterCode: async function(code) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const barber = this.barbers.find(b => b.code === code);
                
                if (barber) {
                    resolve({
                        success: true,
                        message: "Мастер найден",
                        master: {
                            id: barber.id,
                            name: barber.name,
                            code: barber.code,
                            rating: barber.rating,
                            experience: barber.experience,
                            specialization: barber.specialization
                        }
                    });
                } else {
                    resolve({
                        success: false,
                        error: "Мастер с таким кодом не найден"
                    });
                }
            }, 300);
        });
    },

    // Получить расписание мастера
    getMasterSchedule: async function(code) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const schedule = this.schedule[code];
                
                if (schedule) {
                    resolve({
                        success: true,
                        schedule: schedule
                    });
                } else {
                    resolve({
                        success: false,
                        error: "Расписание не найдено"
                    });
                }
            }, 300);
        });
    },

    // Создать запись (клиент)
    createBooking: async function(bookingData) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const booking = {
                    id: Date.now(),
                    ...bookingData,
                    status: 'pending',
                    created: new Date().toISOString()
                };
                
                this.bookings.push(booking);
                
                // Сохраняем в localStorage
                localStorage.setItem('barberBookings', JSON.stringify(this.bookings));
                
                console.log('Запись создана:', booking);
                
                resolve({
                    success: true,
                    message: "Запись успешно создана!",
                    booking: booking
                });
            }, 500);
        });
    },

    // Получить записи барбера
    getBarberBookings: function(barberId) {
        return this.bookings.filter(b => b.barberId === barberId);
    },

    // Обновить статус записи
    updateBookingStatus: async function(bookingId, status) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const booking = this.bookings.find(b => b.id === bookingId);
                
                if (booking) {
                    booking.status = status;
                    booking.updated = new Date().toISOString();
                    
                    localStorage.setItem('barberBookings', JSON.stringify(this.bookings));
                    
                    resolve({
                        success: true,
                        message: "Статус обновлен",
                        booking: booking
                    });
                } else {
                    resolve({
                        success: false,
                        error: "Запись не найдена"
                    });
                }
            }, 300);
        });
    },

    // Получить статистику барбера
    getBarberStats: function(barberId) {
        const barberBookings = this.getBarberBookings(barberId);
        const completed = barberBookings.filter(b => b.status === 'completed').length;
        const pending = barberBookings.filter(b => b.status === 'pending').length;
        const cancelled = barberBookings.filter(b => b.status === 'cancelled').length;
        
        return {
            total: barberBookings.length,
            completed: completed,
            pending: pending,
            cancelled: cancelled,
            completionRate: barberBookings.length > 0 ? 
                Math.round((completed / barberBookings.length) * 100) : 0
        };
    }
};

// Инициализируем систему при загрузке
document.addEventListener('DOMContentLoaded', function() {
    BarberSystem.init();
});

// Экспортируем для использования в других файлах
window.BarberSystem = BarberSystem;