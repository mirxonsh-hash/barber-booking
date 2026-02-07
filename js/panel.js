// js/panel.js - Панель управления барбера
document.addEventListener('DOMContentLoaded', async function() {
    // Проверяем авторизацию
    if (!BarberSystem.isAuthenticated()) {
        window.location.href = 'barber-login.html';
        return;
    }
    
    const barber = BarberSystem.getCurrentBarber();
    if (!barber) {
        BarberSystem.logout();
        window.location.href = 'barber-login.html';
        return;
    }
    
    // Заполняем информацию о барбере
    document.getElementById('barberName').textContent = barber.name;
    document.getElementById('barberCode').textContent = `Код: ${barber.code}`;
    document.getElementById('barberRating').textContent = barber.rating;
    document.getElementById('barberExperience').textContent = barber.experience;
    document.getElementById('masterCodeDisplay').textContent = barber.code;
    
    // Загружаем записи
    await loadBookings();
    
    // Загружаем статистику
    loadStats();
    
    // Кнопка выхода
    document.getElementById('logoutBtn').addEventListener('click', function() {
        BarberSystem.logout();
        window.location.href = 'barber-login.html';
    });
    
    // Кнопка копирования кода
    document.getElementById('copyCodeBtn').addEventListener('click', function() {
        navigator.clipboard.writeText(barber.code)
            .then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check"></i> Скопировано!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
    });
    
    // Обновление статусов записей
    document.addEventListener('click', async function(e) {
        if (e.target.classList.contains('status-btn')) {
            const bookingId = parseInt(e.target.dataset.bookingId);
            const newStatus = e.target.dataset.status;
            
            const result = await BarberSystem.updateBookingStatus(bookingId, newStatus);
            
            if (result.success) {
                await loadBookings();
                loadStats();
            }
        }
    });
    
    async function loadBookings() {
        const bookings = BarberSystem.getBarberBookings(barber.id);
        const container = document.getElementById('bookingsContainer');
        
        if (!container) return;
        
        if (bookings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-calendar-times"></i>
                    <h3>Нет записей</h3>
                    <p>Здесь будут отображаться новые записи клиентов</p>
                </div>
            `;
            return;
        }
        
        // Сортируем по дате (новые сначала)
        bookings.sort((a, b) => new Date(b.created) - new Date(a.created));
        
        container.innerHTML = bookings.map(booking => {
            const date = new Date(booking.date);
            const formattedDate = date.toLocaleDateString('ru-RU', {
                weekday: 'short',
                day: 'numeric',
                month: 'short'
            });
            
            const statusColors = {
                pending: 'warning',
                confirmed: 'info',
                completed: 'success',
                cancelled: 'danger'
            };
            
            const statusTexts = {
                pending: 'Ожидает',
                confirmed: 'Подтверждено',
                completed: 'Выполнено',
                cancelled: 'Отменено'
            };
            
            return `
                <div class="booking-card">
                    <div class="booking-header">
                        <div class="booking-date">
                            <div class="date">${formattedDate}</div>
                            <div class="time">${booking.time}</div>
                        </div>
                        <div class="booking-status status-${statusColors[booking.status]}">
                            ${statusTexts[booking.status]}
                        </div>
                    </div>
                    
                    <div class="booking-info">
                        <div class="client-info">
                            <div class="client-name">
                                <i class="fas fa-user"></i> ${booking.clientName}
                            </div>
                            <div class="client-phone">
                                <i class="fas fa-phone"></i> ${booking.clientPhone}
                            </div>
                        </div>
                        
                        <div class="booking-actions">
                            ${booking.status === 'pending' ? `
                                <button class="btn btn-sm status-btn" data-booking-id="${booking.id}" data-status="confirmed">
                                    <i class="fas fa-check"></i> Подтвердить
                                </button>
                                <button class="btn btn-sm btn-secondary status-btn" data-booking-id="${booking.id}" data-status="cancelled">
                                    <i class="fas fa-times"></i> Отменить
                                </button>
                            ` : ''}
                            
                            ${booking.status === 'confirmed' ? `
                                <button class="btn btn-sm status-btn" data-booking-id="${booking.id}" data-status="completed">
                                    <i class="fas fa-check-circle"></i> Выполнено
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    function loadStats() {
        const stats = BarberSystem.getBarberStats(barber.id);
        
        document.getElementById('totalBookings').textContent = stats.total;
        document.getElementById('completedBookings').textContent = stats.completed;
        document.getElementById('pendingBookings').textContent = stats.pending;
        document.getElementById('completionRate').textContent = `${stats.completionRate}%`;
    }
    
    // Auto-refresh каждые 30 секунд
    setInterval(async () => {
        await loadBookings();
        loadStats();
    }, 30000);
});
