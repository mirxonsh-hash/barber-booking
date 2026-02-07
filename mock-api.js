// Временно используем мок-данные вместо реального API
const MOCK_BARBERS = [
    { id: 1, name: 'Александр', code: 'B-ARBER003' },
    { id: 2, name: 'Иван Иванов', code: 'IVAN123' }
];

const MOCK_SCHEDULE = [
    { date: '2026-02-08', day_name: 'Сб', times: ['10:00', '11:00', '12:00'] },
    { date: '2026-02-09', day_name: 'Вс', times: ['10:00', '11:00', '14:00'] }
];

// Замените API вызовы на мок-данные