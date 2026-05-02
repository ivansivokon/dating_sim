let playerId = null;
let currentState = null;
let currentLocation = 'School';
let activeDialogueGirlId = null;
const LOCATIONS = ['School', 'Park', 'Cafe'];

// Auth
document.getElementById('login-btn').addEventListener('click', login);
document.getElementById('register-btn').addEventListener('click', register);

async function login() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password})
  });
  const data = await res.json();
  if (data.error) return document.getElementById('auth-error').textContent = data.error;
  playerId = data.playerId;
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('game-screen').style.display = 'block';
  loadState();
}

async function register() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username, password})
  });
  const data = await res.json();
  if (data.error) return document.getElementById('auth-error').textContent = data.error;
  playerId = data.playerId;
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('game-screen').style.display = 'block';
  loadState();
}

async function loadState() {
  const res = await fetch('/api/state');
  currentState = await res.json();
  // Найти игрока
  const me = currentState.players.find(p => p.id === playerId);
  if (me) {
    document.getElementById('player-nick').textContent = me.username;
    currentLocation = me.currentLocation;
  }
  renderLocation();
  // Установить активную кнопку локации
  document.querySelectorAll('.loc-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.loc === currentLocation);
  });
}

function renderLocation() {
  const view = document.getElementById('location-view');
  view.className = ''; // сброс
  view.classList.add('location-' + currentLocation.toLowerCase());
  view.innerHTML = '';
  if (!currentState) return;
  const girlsHere = currentState.girls.filter(g => g.currentLocation === currentLocation);
  girlsHere.forEach(g => {
    const card = document.createElement('div');
    card.className = 'girl-card';
    let status = '';
    if (g.boyfriendId === playerId) status = '❤️ Твоя девушка';
    else if (g.boyfriendId) status = 'Занята';
    const btnDisabled = (g.boyfriendId && g.boyfriendId !== playerId) || 
                        currentState.active_dialogues.some(d => d.girlId === g.id);
    card.innerHTML = `
      <div>
        <div class="name">${g.name}</div>
        <div class="status">${status}</div>
      </div>
      <button data-girl="${g.id}" ${btnDisabled ? 'disabled' : ''}>
        ${btnDisabled ? 'Недоступна' : 'Поговорить'}
      </button>
    `;
    view.appendChild(card);
  });
  // Привязка кнопок
  view.querySelectorAll('button[data-girl]').forEach(btn => {
    btn.addEventListener('click', () => startDialogue(btn.dataset.girl));
  });
}

// Локации
document.querySelectorAll('.loc-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const loc = btn.dataset.loc;
    if (loc === currentLocation) return;
    const res = await fetch('/api/move', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({playerId, location: loc})
    });
    const data = await res.json();
    if (data.error) return alert(data.error);
    currentLocation = loc;
    loadState();
  });
});

// Диалог
async function startDialogue(girlId) {
  const res = await fetch('/api/start-dialogue', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({playerId, girlId})
  });
  const data = await res.json();
  if (data.error) return alert(data.error);
  activeDialogueGirlId = girlId;
  const girl = currentState.girls.find(g => g.id === girlId);
  document.getElementById('dialogue-girl-name').textContent = girl ? girl.name : '';
  document.getElementById('chat-messages').innerHTML = '';
  if (data.reply) addMessage(data.reply, 'girl');
  document.getElementById('dialogue-modal').classList.remove('hidden');
  document.getElementById('chat-input').focus();
}

function addMessage(text, sender) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}`;
  msgDiv.textContent = text;
  document.getElementById('chat-messages').appendChild(msgDiv);
  msgDiv.scrollIntoView({behavior: 'smooth'});
}

document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('chat-input').addEventListener('keypress', e => {
  if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || !activeDialogueGirlId) return;
  input.value = '';
  addMessage(text, 'user');
  const res = await fetch('/api/send-message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({playerId, text})
  });
  const data = await res.json();
  if (data.reply) addMessage(data.reply, 'girl');
}

document.getElementById('close-dialogue').addEventListener('click', async () => {
  await fetch('/api/leave-dialogue', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({playerId})
  });
  document.getElementById('dialogue-modal').classList.add('hidden');
  activeDialogueGirlId = null;
  loadState(); // обновить доступность девушек
});