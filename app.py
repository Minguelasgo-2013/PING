#!/usr/bin/env python3
"""
PING - Red social local con Turso (SQLite na nube)
Versión para Render con conexión diferida a Turso
"""

import os
import json
import time
from datetime import datetime
from math import radians, sin, cos, sqrt, asin
from flask import Flask, render_template, request, jsonify, make_response

try:
    import libsql
except ImportError:
    print("⚠️ libsql non está instalado. Executa: pip install libsql")
    exit(1)

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-secreta')

TURSO_DATABASE_URL = os.environ.get('TURSO_DATABASE_URL')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN')

if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
    print("❌ Erro: TURSO_DATABASE_URL e TURSO_AUTH_TOKEN deben estar definidas.")
    exit(1)

# ─── CONEXIÓN DIFERIDA (Lazy) ───
def get_connection():
    """Crea unha nova conexión con Turso ou reconecta se falla."""
    try:
        conn = libsql.connect("ping.db", sync_url=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
        conn.sync()
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar con Turso: {e}")
        return None

def execute_query(query, params=(), retries=2):
    """Executa unha consulta SQL con reintentos e reconexión."""
    conn = None
    for attempt in range(retries + 1):
        try:
            conn = get_connection()
            if not conn:
                raise Exception("Non se puido conectar con Turso")
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                result = cur.fetchall()
            else:
                result = None
            conn.commit()
            # Non pechamos a conexión, deixamos que se recolla ao saír da función
            return result
        except Exception as e:
            print(f"⚠️ Intento {attempt+1} fallou: {e}")
            if attempt == retries:
                raise Exception(f"Erro ao executar consulta despois de {retries+1} intentos: {e}")
            time.sleep(0.5)
    return None

# ─── CREAR TÁBOAS (unha soa vez) ───
try:
    execute_query("""
        CREATE TABLE IF NOT EXISTS post (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            lat REAL,
            lng REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS group_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_by TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    execute_query("""
        CREATE TABLE IF NOT EXISTS group_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Táboas creadas/verificadas en Turso")
except Exception as e:
    print(f"❌ Erro ao crear táboas: {e}")

# ─── ZONAS ───
ZONAS = {
    'lalin': {'nombre': 'Lalín', 'lat': 42.6606, 'lng': -8.1133},
    'cello': {'nombre': 'Cello', 'lat': 42.6500, 'lng': -8.7500},
    'rodeiro': {'nombre': 'Rodeiro', 'lat': 42.6500, 'lng': -7.9500},
    'santiago': {'nombre': 'Santiago', 'lat': 42.8782, 'lng': -8.5448},
    'pontevedra': {'nombre': 'Pontevedra', 'lat': 42.4300, 'lng': -8.6440},
    'ourense': {'nombre': 'Ourense', 'lat': 42.3400, 'lng': -7.8700},
    'vigo': {'nombre': 'Vigo', 'lat': 42.2406, 'lng': -8.7227},
    'coruna': {'nombre': 'A Coruña', 'lat': 43.3623, 'lng': -8.4115}
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

# ─── RUTAS ───

@app.route('/')
def index():
    username = request.cookies.get('ping_username', 'Anónimo')
    return render_template('index.html', username=username)

@app.route('/set_username', methods=['POST'])
def set_username():
    data = request.json
    username = data.get('username', 'Anónimo').strip() or 'Anónimo'
    resp = make_response(jsonify({'success': True, 'username': username}))
    resp.set_cookie('ping_username', username, max_age=60*60*24*30)
    return resp

@app.route('/api/posts')
def api_posts():
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        if not lat or not lng:
            return jsonify([])
        rows = execute_query("SELECT * FROM post ORDER BY created_at DESC LIMIT 50") or []
        result = []
        for row in rows:
            if row[4] and row[5]:
                dist = haversine(lat, lng, row[4], row[5])
                if dist <= 5:
                    result.append({
                        'id': row[0],
                        'username': row[1],
                        'content': row[2],
                        'category': row[3],
                        'lat': row[4],
                        'lng': row[5],
                        'dist': round(dist, 2),
                        'created_at': row[6] if len(row) > 6 else ''
                    })
        return jsonify(result)
    except Exception as e:
        print(f"❌ GET /api/posts: {e}")
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/api/posts', methods=['POST'])
def create_post():
    try:
        data = request.json
        username = request.cookies.get('ping_username', 'Anónimo')
        content = data.get('content')
        category = data.get('category', 'general')
        lat = data.get('lat')
        lng = data.get('lng')
        if not content:
            return jsonify({'error': 'O contido é obrigatorio'}), 400
        execute_query(
            "INSERT INTO post (username, content, category, lat, lng) VALUES (?, ?, ?, ?, ?)",
            (username, content, category, lat, lng)
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ POST /api/posts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups')
def api_groups():
    try:
        username = request.cookies.get('ping_username', 'Anónimo')
        rows = execute_query("SELECT * FROM group_table ORDER BY created_at DESC LIMIT 20") or []
        result = []
        for row in rows:
            group_id = row[0]
            members_count = execute_query("SELECT COUNT(*) FROM group_member WHERE group_id = ?", (group_id,))
            members_count = members_count[0][0] if members_count else 0
            is_member = execute_query("SELECT COUNT(*) FROM group_member WHERE username = ? AND group_id = ?", (username, group_id))
            is_member = is_member[0][0] > 0 if is_member else False
            result.append({
                'id': group_id,
                'name': row[1],
                'description': row[2] or '',
                'members': members_count,
                'is_member': is_member
            })
        return jsonify(result)
    except Exception as e:
        print(f"❌ GET /api/groups: {e}")
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/api/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    try:
        username = request.cookies.get('ping_username', 'Anónimo')
        existing = execute_query("SELECT COUNT(*) FROM group_member WHERE username = ? AND group_id = ?", (username, group_id))
        if existing and existing[0][0] == 0:
            execute_query("INSERT INTO group_member (username, group_id) VALUES (?, ?)", (username, group_id))
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ POST /api/groups/join: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/groups', methods=['POST'])
def create_group():
    try:
        data = request.json
        username = request.cookies.get('ping_username', 'Anónimo')
        name = data.get('name')
        description = data.get('description', '')
        if not name:
            return jsonify({'error': 'O nome é obrigatorio'}), 400
        execute_query(
            "INSERT INTO group_table (name, description, created_by) VALUES (?, ?, ?)",
            (name, description, username)
        )
        row = execute_query("SELECT last_insert_rowid()")
        if row:
            group_id = row[0][0]
            execute_query("INSERT INTO group_member (username, group_id) VALUES (?, ?)", (username, group_id))
            return jsonify({'success': True, 'id': group_id})
        return jsonify({'error': 'Non se puido crear o grupo'}), 500
    except Exception as e:
        print(f"❌ POST /api/groups: {e}")
        return jsonify({'error': str(e)}), 500

# ─── RUTAS DE ZONAS ───
@app.route('/set_zone', methods=['POST'])
def set_zone():
    try:
        data = request.json
        zone_key = data.get('zone')
        if zone_key in ZONAS:
            resp = make_response(jsonify({'success': True, 'zone': zone_key, 'coords': ZONAS[zone_key]}))
            resp.set_cookie('ping_zone', zone_key, max_age=60*60*24*30)
            return resp
        return jsonify({'error': 'Zona non válida'}), 400
    except Exception as e:
        print(f"❌ set_zone: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones')
def get_zones():
    return jsonify([{'id': k, 'nombre': v['nombre'], 'lat': v['lat'], 'lng': v['lng']} for k, v in ZONAS.items()])

@app.route('/api/current_zone')
def get_current_zone():
    zone = request.cookies.get('ping_zone', 'lalin')
    if zone in ZONAS:
        return jsonify({'zone': zone, 'coords': ZONAS[zone]})
    return jsonify({'zone': 'lalin', 'coords': ZONAS['lalin']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
