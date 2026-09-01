// static/js/main.js

// Глобальные переменные
let currentUser = null;
let currentTheme = null;
let weatherData = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// Основная инициализация
async function initApp() {
    try {
        // Загружаем тему
        await loadTheme();
        
        // Загружаем пользователя
        await loadCurrentUser();
        
        // Инициализируем компоненты
        initNavigation();
        initForms();
        initThemeBuilder();
        initWeatherWidget();
        initNotifications();
        
        // Обновляем UI
        updateUI();
    } catch (error) {
        console.error('Ошибка инициализации:', error);
        showToast('Ошибка загрузки приложения', 'error');
    }
}

// Загрузка темы
async function loadTheme() {
    try {
        const response = await fetch('/api/theme/current');
        if (response.ok) {
            currentTheme = await response.json();
            applyTheme(currentTheme);
        }
    } catch (error) {
        console.error('Ошибка загрузки темы:', error);
    }
}

// Применение темы
function applyTheme(theme) {
    if (!theme) return;
    
    const root = document.documentElement;
    root.style.setProperty('--color-primary', theme.primary_color || '#3B82F6');
    root.style.setProperty('--color-secondary', theme.secondary_color || '#10B981');
    root.style.setProperty('--color-header', theme.header_bg || '#1F2937');
    root.style.setProperty('--color-headerText', theme.header_text || '#FFFFFF');
    root.style.setProperty('--color-button', theme.button_bg || '#3B82F6');
    root.style.setProperty('--color-buttonText', theme.button_text || '#FFFFFF');
    root.style.setProperty('--color-footer', theme.footer_bg || '#1F2937');
    root.style.setProperty('--color-footerText', theme.footer_text || '#FFFFFF');
    
    // Обновляем баннер
    const banner = document.querySelector('.banner-bg');
    if (banner && theme.banner_url) {
        banner.style.backgroundImage = `url('${theme.banner_url}')`;
    }
}

// Загрузка текущего пользователя
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            currentUser = await response.json();
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователя:', error);
    }
}

// Инициализация навигации
function initNavigation() {
    // Мобильное меню
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }
    
    // Активная ссылка
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('nav-link-active');
        }
    });
}

// Инициализация форм
function initForms() {
    // Валидация форм
    document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', handleFormSubmit);
    });
    
    // Показ/скрытие пароля
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', togglePassword);
    });
    
    // Автозаполнение телефона
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', formatPhone);
    }
}

// Обработка отправки форм
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('[type="submit"]');
    const formData = new FormData(form);
    
    // Валидация
    if (!validateForm(form)) {
        return;
    }
    
    // Блокируем кнопку
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Загрузка...';
    }
    
    try {
        const response = await fetch(form.action, {
            method: form.method || 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message || 'Успешно!', 'success');
            
            // Редирект если нужно
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1000);
            }
            
            // Обновляем UI
            if (data.user) {
                currentUser = data.user;
                updateUI();
            }
        } else {
            showToast(data.detail || 'Ошибка', 'error');
        }
    } catch (error) {
        console.error('Ошибка отправки формы:', error);
        showToast('Ошибка сети', 'error');
    } finally {
        // Разблокируем кнопку
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Отправить';
        }
    }
}

// Валидация формы
function validateForm(form) {
    let isValid = true;
    
    form.querySelectorAll('[required]').forEach(input => {
        if (!input.value.trim()) {
            showInputError(input, 'Обязательное поле');
            isValid = false;
        } else {
            clearInputError(input);
        }
    });
    
    // Валидация email
    const emailInput = form.querySelector('input[type="email"]');
    if (emailInput && emailInput.value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(emailInput.value)) {
            showInputError(emailInput, 'Некорректный email');
            isValid = false;
        }
    }
    
    // Валидация пароля
    const passwordInput = form.querySelector('input[type="password"]');
    if (passwordInput && passwordInput.value && passwordInput.value.length < 6) {
        showInputError(passwordInput, 'Минимум 6 символов');
        isValid = false;
    }
    
    return isValid;
}

// Показ ошибки поля
function showInputError(input, message) {
    input.classList.add('border-red-500');
    const errorDiv = input.parentElement.querySelector('.error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

// Очистка ошибки поля
function clearInputError(input) {
    input.classList.remove('border-red-500');
    const errorDiv = input.parentElement.querySelector('.error-message');
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
}

// Переключение видимости пароля
function togglePassword(event) {
    const btn = event.target;
    const input = btn.parentElement.querySelector('input');
    
    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = 'Скрыть';
    } else {
        input.type = 'password';
        btn.textContent = 'Показать';
    }
}

// Форматирование телефона
function formatPhone(event) {
    const input = event.target;
    let value = input.value.replace(/\D/g, '');
    
    if (value.length > 0) {
        if (value.length <= 1) {
            value = '+7' + value;
        } else if (value.length <= 4) {
            value = '+7 (' + value.slice(1);
        } else if (value.length <= 7) {
            value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4);
        } else if (value.length <= 9) {
            value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4, 7) + '-' + value.slice(7);
        } else {
            value = '+7 (' + value.slice(1, 4) + ') ' + value.slice(4, 7) + '-' + value.slice(7, 9) + '-' + value.slice(9, 11);
        }
    }
    
    input.value = value;
}

// Инициализация конструктора тем
function initThemeBuilder() {
    const themeForm = document.getElementById('theme-form');
    if (!themeForm) return;
    
    // Предпросмотр цветов
    const colorInputs = themeForm.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('input', () => {
            previewTheme();
        });
    });
    
    // Предпросмотр баннера
    const bannerInput = themeForm.querySelector('input[name="banner_url"]');
    if (bannerInput) {
        bannerInput.addEventListener('input', () => {
            previewTheme();
        });
    }
    
    // Сохранение темы
    themeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        const formData = new FormData(themeForm);
        const themeData = {};
        
        formData.forEach((value, key) => {
            themeData[key] = value;
        });
        
        try {
            const response = await fetch('/api/admin/themes/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(themeData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showToast('Тема сохранена', 'success');
                applyTheme(data.theme);
            } else {
                showToast(data.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            console.error('Ошибка сохранения темы:', error);
            showToast('Ошибка сети', 'error');
        }
    });
}

// Предпросмотр темы
function previewTheme() {
    const themeForm = document.getElementById('theme-form');
    if (!themeForm) return;
    
    const previewTheme = {
        primary_color: themeForm.querySelector('input[name="primary_color"]').value,
        secondary_color: themeForm.querySelector('input[name="secondary_color"]').value,
        header_bg: themeForm.querySelector('input[name="header_bg"]').value,
        header_text: themeForm.querySelector('input[name="header_text"]').value,
        button_bg: themeForm.querySelector('input[name="button_bg"]').value,
        button_text: themeForm.querySelector('input[name="button_text"]').value,
        banner_url: themeForm.querySelector('input[name="banner_url"]').value,
        footer_bg: themeForm.querySelector('input[name="footer_bg"]').value,
        footer_text: themeForm.querySelector('input[name="footer_text"]').value,
    };
    
    applyTheme(previewTheme);
}

// Инициализация виджета погоды
function initWeatherWidget() {
    const weatherWidget = document.getElementById('weather-widget');
    if (!weatherWidget) return;
    
    loadWeather();
    
    // Обновление каждые 30 минут
    setInterval(loadWeather, 30 * 60 * 1000);
}

// Загрузка погоды
async function loadWeather() {
    try {
        const response = await fetch('/api/weather/current');
        if (response.ok) {
            weatherData = await response.json();
            updateWeatherWidget();
        }
    } catch (error) {
        console.error('Ошибка загрузки погоды:', error);
    }
}

// Обновление виджета погоды
function updateWeatherWidget() {
    const weatherWidget = document.getElementById('weather-widget');
    if (!weatherWidget || !weatherData) return;
    
    const current = weatherData.current;
    if (current) {
        const temp = weatherWidget.querySelector('.weather-temp');
        const desc = weatherWidget.querySelector('.weather-desc');
        const icon = weatherWidget.querySelector('.weather-icon');
        
        if (temp) temp.textContent = `${current.temperature}°C`;
        if (desc) desc.textContent = current.description;
        if (icon && current.icon) {
            icon.src = `https://openweathermap.org/img/wn/${current.icon}@2x.png`;
        }
    }
}

// Инициализация уведомлений
function initNotifications() {
    // Запрос разрешения на уведомления
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Проверка новых уведомлений
    checkNotifications();
    setInterval(checkNotifications, 60 * 1000);
}

// Проверка уведомлений
async function checkNotifications() {
    if (!currentUser) return;
    
    try {
        const response = await fetch('/api/notifications');
        if (response.ok) {
            const notifications = await response.json();
            
            notifications.forEach(notification => {
                if (!notification.read) {
                    showNotification(notification);
                }
            });
        }
    } catch (error) {
        console.error('Ошибка проверки уведомлений:', error);
    }
}

// Показ уведомления
function showNotification(notification) {
    // Браузерное уведомление
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.title, {
            body: notification.message,
            icon: '/static/img/logo.png'
        });
    }
    
    // Toast уведомление
    showToast(notification.message, 'info');
}

// Обновление UI
function updateUI() {
    // Обновляем навигацию
    const authLinks = document.querySelectorAll('.auth-link');
    const userMenu = document.getElementById('user-menu');
    
    if (currentUser) {
        // Пользователь авторизован
        authLinks.forEach(link => link.classList.add('hidden'));
        
        if (userMenu) {
            userMenu.classList.remove('hidden');
            const username = userMenu.querySelector('.username');
            if (username) username.textContent = currentUser.username;
        }
        
        // Показываем админ-меню
        if (currentUser.role === 'admin' || currentUser.role === 'moderator') {
            const adminLinks = document.querySelectorAll('.admin-link');
            adminLinks.forEach(link => link.classList.remove('hidden'));
        }
    } else {
        // Пользователь не авторизован
        authLinks.forEach(link => link.classList.remove('hidden'));
        
        if (userMenu) {
            userMenu.classList.add('hidden');
        }
    }
}

// Показ toast уведомления
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Автоматическое удаление через 3 секунды
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Выход из аккаунта
async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });
        
        if (response.ok) {
            currentUser = null;
            updateUI();
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Ошибка выхода:', error);
        showToast('Ошибка выхода', 'error');
    }
}

// Экспорт функций для глобального использования
window.app = {
    logout,
    showToast,
    updateUI
};
