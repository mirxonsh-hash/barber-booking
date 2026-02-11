document.addEventListener('DOMContentLoaded', async () => {
    console.log('📄 barber-profile.js loaded');

    const result = await BarberSystem.checkAuth();

    if (!result.authenticated) {
        console.warn('⛔ Не авторизован — редирект на login');
        window.location.href = '/barber-login?from=profile';
        return;
    }

    loadProfile();

    document.getElementById('logoutBtn').addEventListener('click', () => {
        BarberSystem.logout();
    });

    document.getElementById('saveBtn').addEventListener('click', saveProfile);
});

function loadProfile() {
    console.log('📥 Загружаем профиль');

    const barber = BarberSystem.getCurrentBarber?.();

    if (!barber) {
        console.warn('⚠️ Нет barberData в localStorage');
        return;
    }

    document.getElementById('inputName').value = barber.name || '';
    document.getElementById('inputPhone').value = barber.phone || '';
    document.getElementById('inputEmail').value = barber.email || '';
}

function saveProfile() {
    const name = document.getElementById('inputName').value;
    const phone = document.getElementById('inputPhone').value;
    const email = document.getElementById('inputEmail').value;

    const barber = BarberSystem.getCurrentBarber?.() || {};
    barber.name = name;
    barber.phone = phone;
    barber.email = email;

    localStorage.setItem('barberData', JSON.stringify(barber));

    alert('✅ Профиль сохранён');
}
