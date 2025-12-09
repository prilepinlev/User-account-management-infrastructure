const API_URL = 'http://localhost:8000/api';

// Текущий пользователь
let currentUser = null;

// Проверка авторизации при загрузке страницы
window.onload = function() {
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        showUserArea();
    } else {
        showLogin();
    }
};

// Показать форму входа
function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('usersList').style.display = 'none';
    const adminPanel = document.getElementById('adminPanel');
    if (adminPanel) adminPanel.style.display = 'none';
}

// Показать форму регистрации
function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('usersList').style.display = 'none';
    const adminPanel = document.getElementById('adminPanel');
    if (adminPanel) adminPanel.style.display = 'none';
}

// Показать область пользователя
function showUserArea() {
    console.log('showUserArea() вызвана, currentUser:', currentUser);
    
    document.getElementById('authButtons').style.display = 'none';
    document.getElementById('userInfo').style.display = 'block';
    document.getElementById('username').textContent = `Привет, ${currentUser.username}!`;
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('usersList').style.display = 'block';
    
    if (currentUser.role === 'admin') {
        const adminPanel = document.getElementById('adminPanel');
        if (adminPanel) adminPanel.style.display = 'block';
    }
    
    console.log('Вызываем loadUsers()');
    loadUsers();
}

// Регистрация
async function register(event) {
    event.preventDefault();
    
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    
    console.log('Попытка регистрации:', { username, email });
    
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        console.log('Статус регистрации:', response.status);
        const data = await response.json();
        console.log('Данные ответа регистрации:', data);
        
        if (response.ok) {
            showMessage('Регистрация успешна! Выполняется вход...', 'success');
            document.getElementById('registerFormElement').reset();
            
            // Небольшая задержка перед входом
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Автоматический вход после регистрации
            console.log('Автоматический вход с username:', username);
            const loginResponse = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            console.log('Статус автовхода:', loginResponse.status);
            const loginData = await loginResponse.json();
            console.log('Данные автовхода:', loginData);
            
            if (loginResponse.ok) {
                currentUser = loginData.user;
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                showMessage('Вход выполнен успешно!', 'success');
                showUserArea();
            } else {
                showMessage(loginData.detail || 'Регистрация прошла успешно, но не удалось войти. Попробуйте войти вручную.', 'error');
                showLogin();
            }
        } else {
            showMessage(data.detail || 'Ошибка регистрации', 'error');
        }
    } catch (error) {
        console.error('Ошибка при регистрации:', error);
        showMessage('Ошибка подключения к серверу: ' + error.message, 'error');
    }
}

// Вход
async function login(event) {
    event.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    console.log('Попытка входа:', username);
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        console.log('Статус ответа:', response.status);
        
        const data = await response.json();
        console.log('Данные ответа:', data);
        
        if (response.ok) {
            currentUser = data.user;
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            document.getElementById('loginFormElement').reset();
            console.log('Вызываем showUserArea()');
            // Переключаемся на страницу пользователя
            showUserArea();
            showMessage('Вход выполнен успешно!', 'success');
        } else {
            const errorMsg = data.detail || 'Неверные учётные данные';
            console.error('Ошибка входа:', errorMsg);
            showMessage(errorMsg, 'error');
        }
    } catch (error) {
        console.error('Ошибка при входе:', error);
        showMessage('Ошибка подключения к серверу', 'error');
    }
}

// Выход
function logout() {
    currentUser = null;
    localStorage.removeItem('currentUser');
    document.getElementById('authButtons').style.display = 'block';
    document.getElementById('userInfo').style.display = 'none';
    showLogin();
    showMessage('Вы вышли из системы', 'success');
}

// Загрузка пользователей
async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/users`);
        const data = await response.json();
        
        if (response.ok) {
            displayUsers(data.users);
        } else {
            showMessage('Ошибка загрузки пользователей', 'error');
        }
    } catch (error) {
        showMessage('Ошибка подключения к серверу', 'error');
    }
}

// Отображение пользователей
function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        const date = new Date(user.created_at).toLocaleDateString('ru-RU');
        
        row.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td><span class="role ${user.role}">${user.role}</span></td>
            <td>${date}</td>
            <td>
                ${currentUser && currentUser.role === 'admin' && user.id !== currentUser.id ? 
                    `<button onclick="deleteUser(${user.id})" class="delete-btn">Удалить</button>` 
                    : ''}
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Удаление пользователя (только для админа)
async function deleteUser(userId) {
    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage('Пользователь удалён', 'success');
            loadUsers();
        } else {
            showMessage('Ошибка удаления пользователя', 'error');
        }
    } catch (error) {
        showMessage('Ошибка подключения к серверу', 'error');
    }
}

// Загрузка статистики Redis
async function loadRedisStats() {
    try {
        const response = await fetch(`${API_URL}/redis/stats`);
        const data = await response.json();
        
        const statsDiv = document.getElementById('redisStats');
        const contentDiv = document.getElementById('redisStatsContent');
        
        if (!statsDiv || !contentDiv) return;
        
        if (data.status === 'connected') {
            contentDiv.innerHTML = `
                <p><strong>Статус:</strong> ✅ Подключен</p>
                <p><strong>Версия Redis:</strong> ${data.redis_version}</p>
                <p><strong>Клиенты:</strong> ${data.connected_clients}</p>
                <p><strong>Память:</strong> ${data.used_memory_human}</p>
                <p><strong>Всего подключений:</strong> ${data.total_connections_received}</p>
                <p><strong>Ключей в БД:</strong> ${data.keyspace}</p>
                <p style="color: #856404; margin-top: 10px;">
                    <em>Redis используется для кеширования списка пользователей 
                    и защиты от брутфорса (блокировка после 5 неудачных попыток входа)</em>
                </p>
            `;
            statsDiv.style.display = 'block';
            showMessage('Статистика Redis загружена', 'success');
        } else {
            contentDiv.innerHTML = `<p><strong>Статус:</strong> ❌ ${data.status}</p>`;
            statsDiv.style.display = 'block';
        }
    } catch (error) {
        showMessage('Ошибка получения статистики Redis', 'error');
    }
}

// Показать сообщение
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    if (!messageDiv) return;
    
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}
