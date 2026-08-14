document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand();
    tg.ready();
    tg.setHeaderColor('#0f0f0f');
    tg.setBackgroundColor('#0f0f0f');

    const API_BASE = '';
    const userId = tg.initDataUnsafe?.user?.id;
    const userName = tg.initDataUnsafe?.user?.first_name || 'Пользователь';

    async function loadData() {
        if (!userId) {
            showError('Не удалось получить ID пользователя');
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/api/user/${userId}`);
            if (!res.ok) throw new Error('Failed to load');
            const data = await res.json();
            renderProfile(data.user);
            renderProgress(data.today);
            renderMeals(data.meals);
            renderChart(data.weekly, data.user.target_calories);
        } catch (e) {
            console.error(e);
            showError('Ошибка загрузки данных');
        }
    }

    function renderProfile(user) {
        document.getElementById('user-name').textContent = userName;
        document.getElementById('avatar-letter').textContent = userName.charAt(0).toUpperCase();
        document.getElementById('user-stats').textContent = `ИМТ: ${user.bmi} | Возраст: ${user.age} лет | ${user.weight} кг`;
        document.getElementById('bmi-value').textContent = user.bmi;
        document.getElementById('bmr-value').textContent = Math.round(user.bmr);
        document.getElementById('target-value').textContent = Math.round(user.target_calories);
        document.getElementById('weight-current').textContent = user.weight + ' кг';
        document.getElementById('weight-target').textContent = user.target_weight + ' кг';
    }

    function renderProgress(today) {
        const current = today.calories || 0;
        const target = today.target || 2000;
        const ratio = Math.min(current / target, 1);
        document.getElementById('progress-ratio').textContent = `${Math.round(current)} / ${Math.round(target)} ккал`;
        document.getElementById('progress-bar').style.width = `${ratio * 100}%`;
        document.getElementById('protein-value').textContent = `${Math.round(today.protein || 0)}г`;
        document.getElementById('fat-value').textContent = `${Math.round(today.fat || 0)}г`;
        document.getElementById('carbs-value').textContent = `${Math.round(today.carbs || 0)}г`;
        const remaining = Math.max(target - current, 0);
        document.getElementById('remaining-calories').textContent = `Осталось: ${Math.round(remaining)} ккал`;
    }

    function renderMeals(meals) {
        const container = document.getElementById('meals-list');
        if (!meals || meals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">🍽</span>
                    <p>Сегодня еще не было приемов пищи</p>
                </div>`;
            return;
        }
        const typeIcons = { breakfast: '🌅', lunch: '☀️', dinner: '🌙', snack: '🍿', other: '🍽' };
        const typeNames = { breakfast: 'Завтрак', lunch: 'Обед', dinner: 'Ужин', snack: 'Перекус', other: 'Другое' };
        container.innerHTML = meals.slice(0, 10).map(m => `
            <div class="meal-item">
                <div class="meal-icon">${typeIcons[m.meal_type] || '🍽'}</div>
                <div class="meal-info">
                    <div class="meal-name">${escapeHtml(m.description || 'Неизвестно')}</div>
                    <div class="meal-type">${typeNames[m.meal_type] || 'Другое'}</div>
                </div>
                <div class="meal-calories">${Math.round(m.calories)}</div>
            </div>`).join('');
    }

    function renderChart(weekly, target) {
        const container = document.getElementById('weekly-chart');
        if (!weekly || weekly.length === 0) {
            container.innerHTML = '<div class="chart-placeholder">Нет данных</div>';
            return;
        }
        const maxVal = Math.max(...weekly.map(d => d.calories), target * 1.2);
        const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
        const sorted = weekly.slice().reverse();
        container.innerHTML = sorted.map(d => {
            const h = (d.calories / maxVal) * 140;
            const date = new Date(d.date);
            const dayName = days[date.getDay()];
            const isOver = d.calories > target;
            return `
                <div class="chart-bar-wrapper">
                    <div class="chart-bar ${isOver ? 'over' : ''}" style="height: ${Math.max(h, 4)}px"></div>
                    <span class="chart-label">${dayName}</span>
                </div>`;
        }).join('');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showError(msg) {
        document.querySelector('.main').innerHTML = `<div class="empty-state" style="padding: 60px 20px;"><span class="empty-icon">⚠️</span><p>${msg}</p></div>`;
    }

    loadData();
});
