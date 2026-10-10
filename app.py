import sqlite3, random, uuid, datetime
from flask import Flask, request, jsonify
import os
app = Flask(__name__)
DB='db.db'
ALL_RANGES = {1:(10,20),2:(21,30),3:(31,40),4:(41,50),5:(51,60),6:(61,70),7:(71,80),8:(81,90),9:(91,100)}
def init():
    conn=sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS members (member_id TEXT PRIMARY KEY, phone TEXT, range_source TEXT, range_number INTEGER, min_amount INTEGER, max_amount INTEGER, actual_amount INTEGER, max_contribution_calc INTEGER, range_charge INTEGER, max_payment_status TEXT, range_charge_payment_status TEXT, max_payment_ref TEXT, range_payment_ref TEXT, group_id TEXT, reg_date TEXT, membership_status TEXT)''')
    conn.execute('CREATE TABLE IF NOT EXISTS max_payments (phone TEXT, range_number INTEGER, status TEXT, ref TEXT, PRIMARY KEY(phone, range_number))')
    conn.execute('CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, range_number INTEGER, members_count INTEGER, status TEXT)')
    conn.commit(); conn.close()
init()
@app.route('/ranges')
def ranges():
    source=request.args.get('source','ordinary')
    conn=sqlite3.connect(DB); rows=list(conn.execute('SELECT range_number, COUNT(*) FROM members GROUP BY range_number')); counts={r:c for r,c in rows}; conn.close()
    if source=='participating':
        if not rows: return jsonify({"empty":True,"message":"No one participated yet. Press Button 2 first."})
        avail=[r for r,_ in rows]
        while len(avail)<5: avail+=avail
        sel=random.sample(avail,5) if len(set(avail))>=5 else random.choices(avail,k=5)
        out=[{"range_number":k,"min":ALL_RANGES[k][0],"max":ALL_RANGES[k][1],"label":f"KSh {ALL_RANGES[k][0]}-{ALL_RANGES[k][1]}","range_charge":8*k,"max_contribution":ALL_RANGES[k][1]*10,"people_already":counts.get(k,0),"source":source} for k in sel]
        return jsonify(out)
    else:
        sel=random.sample(list(ALL_RANGES.keys()),5)
        out=[{"range_number":k,"min":ALL_RANGES[k][0],"max":ALL_RANGES[k][1],"label":f"KSh {ALL_RANGES[k][0]}-{ALL_RANGES[k][1]}","range_charge":8*k,"max_contribution":ALL_RANGES[k][1]*10,"people_already":0,"source":source} for k in sel]
        return jsonify(out)
@app.route('/join', methods=['POST'])
def join():
    d=request.json; phone=d['phone']; rn=int(d['range_number']); source=d['range_source']; actual=int(d['actual_amount']); mn,mx=ALL_RANGES[rn]
    if actual<mn or actual>mx: return jsonify({"error":f"Amount must be {mn}-{mx}"}),400
    max_contrib=mx*10; charge=8*rn; conn=sqlite3.connect(DB)
    exist=conn.execute('SELECT status FROM max_payments WHERE phone=? AND range_number=?',(phone,rn)).fetchone()
    max_ref=None; max_status="ALREADY_PAID" if exist else "NEEDS_PAYMENT"
    if not exist:
        max_ref=f"MAX-{uuid.uuid4().hex[:8]}"; conn.execute('INSERT INTO max_payments VALUES (?,?,?,?)',(phone,rn,'SUCCESS',max_ref)); max_status="SUCCESS_PAID_NOW"
    gid=f"GRP-{rn}"; grp=conn.execute('SELECT members_count FROM groups WHERE group_id=?',(gid,)).fetchone()
    if not grp: conn.execute('INSERT INTO groups VALUES (?,?,?,?)',(gid,rn,0,'OPEN')); cnt=0
    else: cnt=grp[0]
    if cnt>=10: conn.close(); return jsonify({"error":"Group full 10"}),400
    mid=str(uuid.uuid4()); conn.execute('INSERT INTO members VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(mid,phone,source,rn,mn,mx,actual,max_contrib,charge,max_status,'SUCCESS',max_ref,f"RNG-{uuid.uuid4().hex[:4]}",gid,datetime.datetime.now().isoformat(),'ELIGIBLE'))
    conn.execute('UPDATE groups SET members_count=members_count+1 WHERE group_id=?',(gid,))
    new=conn.execute('SELECT members_count FROM groups WHERE group_id=?',(gid,)).fetchone()[0]
    if new>=10: conn.execute('UPDATE groups SET status=? WHERE group_id=?',('FULL',gid))
    conn.commit(); total=conn.execute('SELECT SUM(actual_amount) FROM members WHERE group_id=?',(gid,)).fetchone()[0] or 0; conn.close()
    return jsonify({"group_id":gid,"group_members":new,"group_status":"FULL" if new>=10 else f"OPEN {new}/10","total_for_beneficiary":total if new>=10 else f"Waiting {new}/10","beneficiary_paid":total if new>=10 else False,"max_payment_status":max_status})
@app.route('/')
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port))
