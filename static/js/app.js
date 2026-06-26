let userLocation = null;
let map = null;
let markers = [];
let currentSection = 'feed';

// ──────────────── GEOLOCALIZACIÓN ────────────────
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                loadFeed();
                initMap();
            },
            () => {
                userLocation = { lat: 42.6606, lng: -8.1133 }; // Lalín por defecto
                loadFeed();
                initMap();
            }
        );
    } else {
        userLocation = { lat: 42.6606, lng: -8.1133 };
        loadFeed();
        initMap();
    }
}

// ──────────────── FEED ────────────────
async function loadFeed() {
    if (!userLocation) return;
    const feed = document.getElementById('feed-list');
    feed.innerHTML = '<div style="text-align:center;color:#8b949e;padding:2rem;">Cargando...</div>';
    try {
        const res = await fetch(`/api/posts?lat=${userLocation.lat}&lng=${userLocation.lng}`);
        const posts = await res.json();
        if (posts.length === 0) {
            feed.innerHTML = '<div style="text-align:center;color:#8b949e;padding:2rem;">No hay avisos cerca. ¡Sé el primero en publicar!</div>';
            return;
        }
        feed.innerHTML = posts.map(p => `
            <div class="post-card">
                <div class="post-header">
                    <span class="post-avatar">👤</span>
                    <span class="post-user">${escapeHtml(p.username)}</span>
                    <span class="post-distance">${p.dist} km</span>
                </div>
                <div class="post-content">${escapeHtml(p.content)}</div>
                <span class="post-category">${p.category}</span>
                <div class="post-time">${p.created_at}</div>
            </div>
        `).join('');
    } catch (e) {
        feed.innerHTML = '<div style="color:#f85149;text-align:center;">Error al cargar el feed</div>';
    }
}

// ──────────────── MAPA ────────────────
function initMap() {
    if (map) return;
    map = L.map('map').setView([userLocation.lat, userLocation.lng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);
    L.circleMarker([userLocation.lat, userLocation.lng], {
        radius: 8,
        fillColor: '#58a6ff',
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(map).bindPopup('📍 Tú estás aquí');
    loadMapPosts();
}

async function loadMapPosts() {
    if (!map || !userLocation) return;
    try {
        const res = await fetch(`/api/posts?lat=${userLocation.lat}&lng=${userLocation.lng}`);
        const posts = await res.json();
        markers.forEach(m => map.removeLayer(m));
        markers = [];
        posts.forEach(p => {
            if (p.lat && p.lng) {
                const marker = L.marker([p.lat, p.lng])
                    .bindPopup(`<strong>${escapeHtml(p.username)}</strong><br>${escapeHtml(p.content)}<br><span style="color:#8b949e;font-size:0.8rem;">${p.category} • ${p.dist} km</span>`)
                    .addTo(map);
                markers.push(marker);
            }
        });
    } catch (e) { console.error('Error loading map posts'); }
}

// ──────────────── PUBLICAR ────────────────
function showPostForm() {
    document.getElementById('post-modal').classList.add('open');
    document.getElementById('post-content').value = '';
}

function closeModal(id) {
    document.getElementById(id).classList.remove('open');
}

async function submitPost() {
    const content = document.getElementById('post-content').value.trim();
    const category = document.getElementById('post-category').value;
    if (!content) { alert('Escribe algo'); return; }
    try {
        await fetch('/api/posts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, category, lat: userLocation ? userLocation.lat : null, lng: userLocation ? userLocation.lng : null })
        });
        closeModal('post-modal');
        loadFeed();
        loadMapPosts();
    } catch (e) { alert('Error al publicar'); }
}

// ──────────────── NOMBRE DE USUARIO ────────────────
function changeUsername() {
    document.getElementById('username-modal').classList.add('open');
    document.getElementById('username-input').value = document.getElementById('username-display').textContent.trim();
}

async function saveUsername() {
    const username = document.getElementById('username-input').value.trim() || 'Anónimo';
    try {
        await fetch('/set_username', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        document.getElementById('username-display').textContent = username;
        closeModal('username-modal');
    } catch (e) { alert('Error al cambiar nombre'); }
}

// ──────────────── GRUPOS ────────────────
async function loadGroups() {
    const list = document.getElementById('groups-list');
    try {
        const res = await fetch('/api/groups');
        const groups = await res.json();
        if (groups.length === 0) {
            list.innerHTML = '<div style="text-align:center;color:#8b949e;padding:2rem;">No hay grupos. ¡Crea el primero!</div>';
            return;
        }
        list.innerHTML = groups.map(g => `
            <div class="group-card">
                <div class="group-name">${escapeHtml(g.name)}</div>
                <div class="group-desc">${escapeHtml(g.description || '')}</div>
                <div class="group-members">👥 ${g.members} miembros</div>
                <div class="group-actions">
                    ${g.is_member ? '<span style="color:#3fb950;">✅ Miembro</span>' :
                    `<button onclick="joinGroup(${g.id})" class="btn-primary" style="width:auto;padding:0.3rem 0.8rem;font-size:0.8rem;">Unirse</button>`}
                </div>
            </div>
        `).join('');
    } catch (e) { list.innerHTML = '<div style="color:#f85149;">Error al cargar grupos</div>'; }
}

async function joinGroup(groupId) {
    try {
        await fetch(`/api/groups/${groupId}/join`, { method: 'POST' });
        loadGroups();
    } catch (e) { alert('Error al unirse al grupo'); }
}

function showCreateGroup() {
    document.getElementById('group-modal').classList.add('open');
    document.getElementById('group-name').value = '';
    document.getElementById('group-desc').value = '';
}

async function submitGroup() {
    const name = document.getElementById('group-name').value.trim();
    const description = document.getElementById('group-desc').value.trim();
    if (!name) { alert('El nombre es obligatorio'); return; }
    try {
        await fetch('/api/groups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        closeModal('group-modal');
        loadGroups();
    } catch (e) { alert('Error al crear grupo'); }
}

// ──────────────── ZONAS ────────────────
async function loadZones() {
    try {
        const res = await fetch('/api/zones');
        const zones = await res.json();
        const container = document.getElementById('zone-list');
        container.innerHTML = zones.map(z => `
            <button onclick="setZone('${z.id}')" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:0.6rem 1rem;color:#e6edf3;cursor:pointer;font-size:0.9rem;text-align:left;">
                📍 ${z.nombre}
            </button>
        `).join('');
    } catch (e) {
        console.error('Error loading zones');
    }
}

function showZoneSelector() {
    document.getElementById('zone-modal').classList.add('open');
    loadZones();
}

async function setZone(zoneId) {
    try {
        const res = await fetch('/set_zone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ zone: zoneId })
        });
        const data = await res.json();
        if (data.success) {
            userLocation = { lat: data.coords.lat, lng: data.coords.lng };
            if (map) {
                map.setView([userLocation.lat, userLocation.lng], 13);
                markers.forEach(m => map.removeLayer(m));
                markers = [];
                L.circleMarker([userLocation.lat, userLocation.lng], {
                    radius: 8,
                    fillColor: '#58a6ff',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(map).bindPopup('📍 Zona seleccionada');
            }
            loadFeed();
            loadMapPosts();
            closeModal('zone-modal');
        }
    } catch (e) {
        alert('Error al cambiar de zona');
    }
}

// ──────────────── NAVEGACIÓN ────────────────
function navigateTo(sectionId) {
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-target="${sectionId}"]`).classList.add('active');
    currentSection = sectionId;
    if (sectionId === 'map-view' && map) { setTimeout(() => map.invalidateSize(), 100); }
    if (sectionId === 'groups-view') { loadGroups(); }
    if (sectionId === 'profile-view') { loadProfile(); }
}

// ──────────────── PERFIL ────────────────
async function loadProfile() {
    const container = document.getElementById('profile-content');
    const username = document.getElementById('username-display').textContent.trim();
    container.innerHTML = `
        <div class="profile-avatar">👤</div>
        <div class="profile-username">${escapeHtml(username)}</div>
        <div class="profile-bio">Vives en ${userLocation ? userLocation.lat.toFixed(4) + ', ' + userLocation.lng.toFixed(4) : 'ubicación desconocida'}</div>
        <div style="text-align:center;color:#8b949e;font-size:0.8rem;">📍 Tu ubicación se usa para mostrarte avisos cercanos</div>
        <div style="margin-top:1rem;text-align:center;">
            <button onclick="changeUsername()" class="btn-primary" style="width:auto;padding:0.3rem 1rem;font-size:0.8rem;">✏️ Cambiar nombre</button>
        </div>
    `;
}

// ──────────────── UTILS ────────────────
function escapeHtml(text) { if (!text) return ''; return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function refreshFeed() { loadFeed(); loadMapPosts(); }

// ──────────────── INICIALIZAR ────────────────
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', function() { navigateTo(this.dataset.target); });
    });
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) { if (e.target === this) this.classList.remove('open'); });
    });
    getLocation();
    loadGroups();
});