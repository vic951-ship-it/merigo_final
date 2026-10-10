import os, sqlite3
from flask import Flask, render_template, request, jsonify
app = Flask(__name__)
DATABASE = 'db.db'
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, members_count INTEGER DEFAULT 0, status TEXT DEFAULT "OPEN")')
    conn.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, group_id TEXT, actual_amount REAL DEFAULT 0, phone TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    conn.commit(); conn.close()
init_db()
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/join', methods=['POST'])
def join_group():
    data = request.get_json()
    gid = data.get('group_id', 'merigo-1')
    amount = data.get('amount', 100)
    phone = data.get('phone', '')
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO groups (group_id, members_count, status) VALUES (?, 0, "OPEN")', (gid,))
    conn.execute('INSERT INTO members (group_id, actual_amount, phone) VALUES (?,?,?)', (gid, amount, phone))
    conn.execute('UPDATE groups SET members_count=members_count+1 WHERE group_id=?', (gid,))
    new = conn.execute('SELECT members_count FROM groups WHERE group_id=?', (gid,)).fetchone()[0]
    if new >= 10:
        conn.execute('UPDATE groups SET status=? WHERE group_id=?', ('FULL', gid))
    conn.commit()
    total = conn.execute('SELECT SUM(actual_amount) FROM members WHERE group_id=?', (gid,)).fetchone()[0] or 0
    conn.close()
    max_status = "PAID" if new >= 10 else "PENDING"
    return jsonify({"group_id": gid, "group_members": new, "group_status": "FULL" if new >= 10 else f"OPEN {new}/10", "total_for_beneficiary": total if new >= 10 else f"Waiting {new}/10", "beneficiary_paid": total if new >= 10 else False, "max_payment_status": max_status})
@app.route('/status/<group_id>')
def group_status(group_id):
    conn = get_db()
    g_data = conn.execute('SELECT * FROM groups WHERE group_id=?', (group_id,)).fetchone()
    if not g_data:
        conn.close()
        return jsonify({"error": "group not found"}), 404
    total = conn.execute('SELECT SUM(actual_amount) FROM members WHERE group_id=?', (group_id,)).fetchone()[0] or 0
    conn.close()
    return jsonify({"group_id": group_id, "members": g_data['members_count'], "status": g_data['status'], "total": total})
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
