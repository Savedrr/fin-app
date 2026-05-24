"""
FinanceApp — Controle Financeiro Familiar
Flask + sqlite3 nativo (sem dependências externas de ORM ou login)
"""
import os, json, re, sqlite3, hashlib, secrets
from datetime import datetime, date
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, g

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
DB_PATH = os.path.join(os.path.dirname(__file__), 'financeapp.db')

# ── DB ───────────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def qry(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def run(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def r2d(row): return dict(row) if row else None

# ── Auth ─────────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json: return jsonify({'error':'Não autenticado'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    uid = session.get('user_id')
    return r2d(qry("SELECT * FROM users WHERE id=?", (uid,), one=True)) if uid else None

# ── Init DB ──────────────────────────────────────────────────────────────────
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, avatar_color TEXT DEFAULT '#1DB976',
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, icon TEXT DEFAULT '💰',
        color TEXT DEFAULT '#1D9E75', is_default INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL, amount REAL NOT NULL,
        transaction_type TEXT NOT NULL, category_id INTEGER,
        user_id INTEGER NOT NULL, transaction_date TEXT DEFAULT (date('now')),
        notes TEXT DEFAULT '', month INTEGER, year INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS fixed_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, amount REAL NOT NULL, due_day INTEGER DEFAULT 1,
        category TEXT DEFAULT 'Casa', icon TEXT DEFAULT '📄',
        user_id INTEGER NOT NULL, is_paid INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL, amount REAL NOT NULL,
        monthly_average REAL DEFAULT 0, source TEXT DEFAULT 'Salário',
        user_id INTEGER NOT NULL, received_date TEXT DEFAULT (date('now')),
        month INTEGER, year INTEGER, created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cats = [('Alimentação','🍽️','#E85D04'),('Mercado','🛒','#1D9E75'),
            ('Transporte','🚗','#185FA5'),('Saúde','💊','#D62828'),
            ('Lazer','🎬','#7B2D8B'),('Casa','🏠','#8338EC'),
            ('Educação','📚','#3A86FF'),('Roupas','👗','#FF6B9D'),
            ('Cartão de Crédito','💳','#FB5607'),('Igreja','⛪','#FFBE0B'),
            ('Emergência','🆘','#E63946'),('Outros','💰','#6C757D')]
    for name, icon, color in cats:
        if not db.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone():
            db.execute("INSERT INTO categories (name,icon,color,is_default) VALUES (?,?,?,1)", (name,icon,color))
    for name, email, color in [('Você','voce@email.com','#185FA5'),('Esposa','esposa@email.com','#FF6B9D')]:
        if not db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            db.execute("INSERT INTO users (name,email,password_hash,avatar_color) VALUES (?,?,?,?)",
                      (name, email, hash_pw('123456'), color))
    db.commit(); db.close()

# ── Dashboard helpers ─────────────────────────────────────────────────────────
def get_dashboard_data(month, year):
    incomes = qry("SELECT amount FROM incomes WHERE month=? AND year=?", (month, year))
    total_income = sum(r['amount'] for r in incomes)

    expenses = qry("""SELECT t.amount, c.name as cat_name, c.icon as cat_icon, c.color as cat_color
        FROM transactions t LEFT JOIN categories c ON t.category_id=c.id
        WHERE t.month=? AND t.year=? AND t.transaction_type='expense'""", (month, year))
    total_expenses = sum(r['amount'] for r in expenses)

    fixed_bills_rows = qry("SELECT * FROM fixed_bills WHERE is_active=1 ORDER BY due_day")
    total_fixed = sum(b['amount'] for b in fixed_bills_rows)

    total_spent = total_expenses + total_fixed
    balance = total_income - total_spent
    pct = round(total_spent / total_income * 100, 1) if total_income > 0 else 0

    cat_map = {}
    for t in expenses:
        k = t['cat_name'] or 'Outros'
        if k not in cat_map:
            cat_map[k] = {'name':k, 'icon':t['cat_icon'] or '💰', 'color':t['cat_color'] or '#888', 'total':0}
        cat_map[k]['total'] += t['amount']
    if total_fixed > 0:
        cat_map['Contas Fixas'] = {'name':'Contas Fixas','icon':'📄','color':'#D85A30','total':total_fixed}
    cats_sorted = sorted(cat_map.values(), key=lambda x: x['total'], reverse=True)

    pm, py = (month-1, year) if month > 1 else (12, year-1)
    prev_exp = qry("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE month=? AND year=? AND transaction_type='expense'", (pm,py), one=True)
    prev_total = (prev_exp['t'] if prev_exp else 0) + total_fixed

    alerts = build_alerts(total_income, total_spent, total_fixed, cat_map, balance, prev_total)

    recent = qry("""SELECT t.id, t.description, t.amount, t.transaction_type, t.transaction_date,
        c.name as cat_name, c.icon as cat_icon, c.color as cat_color,
        u.name as user_name, u.avatar_color as user_color
        FROM transactions t LEFT JOIN categories c ON t.category_id=c.id
        LEFT JOIN users u ON t.user_id=u.id
        WHERE t.month=? AND t.year=? ORDER BY t.created_at DESC LIMIT 10""", (month, year))

    def tx_fmt(t): return {'id':t['id'],'description':t['description'],'amount':t['amount'],
        'transaction_type':t['transaction_type'],'transaction_date':t['transaction_date'],
        'category':{'name':t['cat_name'] or 'Outros','icon':t['cat_icon'] or '💰','color':t['cat_color'] or '#888'},
        'user':{'name':t['user_name'] or '—','avatar_color':t['user_color'] or '#888'}}
    def bill_fmt(b): return {'id':b['id'],'name':b['name'],'amount':b['amount'],'due_day':b['due_day'],
        'category':b['category'],'icon':b['icon'],'is_paid':bool(b['is_paid']),'is_active':bool(b['is_active'])}

    return {'month':month,'year':year,'total_income':total_income,'total_expenses':total_expenses,
            'total_fixed':total_fixed,'total_spent':total_spent,'balance':balance,'pct_committed':pct,
            'categories':cats_sorted,'alerts':alerts,
            'recent_transactions':[tx_fmt(t) for t in recent],
            'fixed_bills':[bill_fmt(b) for b in fixed_bills_rows]}

def build_alerts(total_income, total_spent, total_fixed, cat_map, balance, prev_total):
    alerts = []
    food = cat_map.get('Alimentação',{}).get('total',0) + cat_map.get('Mercado',{}).get('total',0)
    if total_income > 0 and food/total_income > 0.30:
        alerts.append({'type':'warning','icon':'🛒','text':f'Vocês gastaram {food/total_income*100:.0f}% da renda com alimentação. Recomendado: até 30%.'})
    if balance > 0:
        alerts.append({'type':'info','icon':'💰','text':f'Restam R$ {balance:,.2f} disponíveis este mês. Que tal guardar parte na reserva?'})
    elif balance < 0:
        alerts.append({'type':'danger','icon':'⚠️','text':f'Atenção! Os gastos ultrapassaram a renda em R$ {abs(balance):,.2f}.'})
    if prev_total > 0 and total_spent < prev_total:
        alerts.append({'type':'success','icon':'🎉','text':f'Vocês gastaram R$ {prev_total-total_spent:,.2f} a menos que no mês passado!'})
    elif prev_total > 0 and total_spent > prev_total * 1.1:
        alerts.append({'type':'warning','icon':'📈','text':'Os gastos aumentaram em relação ao mês passado. Fique de olho!'})
    if total_income > 0 and total_fixed/total_income > 0.50:
        alerts.append({'type':'danger','icon':'🏠','text':f'Contas fixas comprometem {total_fixed/total_income*100:.0f}% da sua renda. Tente renegociar.'})
    return alerts[:4]


# ── PWA Routes ────────────────────────────────────────────────────────────────
@app.route('/static/sw.js')
def service_worker():
    """Service Worker precisa ser servido com header especial de escopo"""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/manifest.json')
def manifest():
    """Manifest na raiz também (alguns browsers pedem aqui)"""
    from flask import send_from_directory
    return send_from_directory('static', 'manifest.json')

# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route('/')
def index(): return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        d = request.get_json()
        user = qry("SELECT * FROM users WHERE email=?", (d.get('email','').lower().strip(),), one=True)
        if user and user['password_hash'] == hash_pw(d.get('password','')):
            session.update({'user_id':user['id'],'user_name':user['name'],'user_color':user['avatar_color']})
            return jsonify({'success':True,'redirect':url_for('dashboard')})
        return jsonify({'success':False,'message':'Email ou senha incorretos'}), 401
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/register', methods=['POST'])
def register():
    d = request.get_json()
    name, email, pw, color = d.get('name','').strip(), d.get('email','').lower().strip(), d.get('password',''), d.get('color','#1DB976')
    if not name or not email or not pw: return jsonify({'success':False,'message':'Preencha todos os campos'}), 400
    if qry("SELECT id FROM users WHERE email=?", (email,), one=True): return jsonify({'success':False,'message':'Email já cadastrado'}), 400
    uid = run("INSERT INTO users (name,email,password_hash,avatar_color) VALUES (?,?,?,?)", (name,email,hash_pw(pw),color))
    session.update({'user_id':uid,'user_name':name,'user_color':color})
    return jsonify({'success':True,'redirect':url_for('dashboard')})

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html', user=current_user())

@app.route('/chat')
@login_required
def chat(): return render_template('chat.html', user=current_user())

@app.route('/lancamentos')
@login_required
def lancamentos(): return render_template('lancamentos.html', user=current_user())

@app.route('/fixas')
@login_required
def fixas(): return render_template('fixas.html', user=current_user())

@app.route('/receitas')
@login_required
def receitas(): return render_template('receitas.html', user=current_user())

@app.route('/relatorios')
@login_required
def relatorios(): return render_template('relatorios.html', user=current_user())

# ── API: Dashboard ────────────────────────────────────────────────────────────
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    today = date.today()
    m = request.args.get('month', today.month, type=int)
    y = request.args.get('year', today.year, type=int)
    return jsonify(get_dashboard_data(m, y))

# ── API: Transactions ─────────────────────────────────────────────────────────
@app.route('/api/transactions')
@login_required
def api_get_transactions():
    today = date.today()
    m = request.args.get('month', today.month, type=int)
    y = request.args.get('year', today.year, type=int)
    rows = qry("""SELECT t.id, t.description, t.amount, t.transaction_type, t.transaction_date, t.notes,
        c.name as cat_name, c.icon as cat_icon, c.color as cat_color,
        u.name as user_name, u.avatar_color as user_color
        FROM transactions t LEFT JOIN categories c ON t.category_id=c.id
        LEFT JOIN users u ON t.user_id=u.id
        WHERE t.month=? AND t.year=? ORDER BY t.transaction_date DESC, t.created_at DESC""", (m, y))
    return jsonify([{'id':t['id'],'description':t['description'],'amount':t['amount'],
        'transaction_type':t['transaction_type'],'transaction_date':t['transaction_date'],'notes':t['notes'],
        'category':{'name':t['cat_name'] or 'Outros','icon':t['cat_icon'] or '💰','color':t['cat_color'] or '#888'},
        'user':{'name':t['user_name'] or '—','avatar_color':t['user_color'] or '#888'}} for t in rows])

@app.route('/api/transactions', methods=['POST'])
@login_required
def api_add_transaction():
    d = request.get_json()
    cat_id = d.get('category_id')
    if not cat_id:
        cat = qry("SELECT id FROM categories WHERE lower(name)=lower(?)", (d.get('category_name','Outros'),), one=True)
        if not cat: cat = qry("SELECT id FROM categories WHERE name='Outros'", one=True)
        cat_id = cat['id'] if cat else None
    try: dt = datetime.fromisoformat(d.get('transaction_date', str(date.today()))).date()
    except: dt = date.today()
    tid = run("""INSERT INTO transactions (description,amount,transaction_type,category_id,user_id,transaction_date,notes,month,year)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (d['description'],float(d['amount']),d.get('transaction_type','expense'),
         cat_id,session['user_id'],str(dt),d.get('notes',''),dt.month,dt.year))
    return jsonify({'success':True,'id':tid})

@app.route('/api/transactions/<int:tid>', methods=['DELETE'])
@login_required
def api_delete_transaction(tid):
    run("DELETE FROM transactions WHERE id=?", (tid,))
    return jsonify({'success':True})

# ── API: Fixed Bills ──────────────────────────────────────────────────────────
@app.route('/api/fixed-bills')
@login_required
def api_get_fixed_bills():
    rows = qry("SELECT * FROM fixed_bills WHERE is_active=1 ORDER BY due_day")
    return jsonify([{**r2d(b),'is_paid':bool(b['is_paid'])} for b in rows])

@app.route('/api/fixed-bills', methods=['POST'])
@login_required
def api_add_fixed_bill():
    d = request.get_json()
    bid = run("INSERT INTO fixed_bills (name,amount,due_day,category,icon,user_id) VALUES (?,?,?,?,?,?)",
              (d['name'],float(d['amount']),int(d.get('due_day',1)),d.get('category','Casa'),d.get('icon','📄'),session['user_id']))
    return jsonify({'success':True,'id':bid})

@app.route('/api/fixed-bills/<int:bid>', methods=['PUT'])
@login_required
def api_update_fixed_bill(bid):
    d = request.get_json()
    fields = {k:d[k] for k in ('name','amount','due_day','category','icon','is_paid','is_active') if k in d}
    if fields:
        sets = ', '.join(f"{k}=?" for k in fields)
        run(f"UPDATE fixed_bills SET {sets} WHERE id=?", (*fields.values(), bid))
    return jsonify({'success':True})

@app.route('/api/fixed-bills/<int:bid>', methods=['DELETE'])
@login_required
def api_delete_fixed_bill(bid):
    run("UPDATE fixed_bills SET is_active=0 WHERE id=?", (bid,))
    return jsonify({'success':True})

# ── API: Incomes ──────────────────────────────────────────────────────────────
@app.route('/api/incomes')
@login_required
def api_get_incomes():
    today = date.today()
    m = request.args.get('month', today.month, type=int)
    y = request.args.get('year', today.year, type=int)
    rows = qry("""SELECT i.*, u.name as user_name, u.avatar_color as user_color
        FROM incomes i LEFT JOIN users u ON i.user_id=u.id
        WHERE i.month=? AND i.year=? ORDER BY i.received_date DESC""", (m, y))
    return jsonify([{'id':i['id'],'description':i['description'],'amount':i['amount'],
        'monthly_average':i['monthly_average'],'source':i['source'],'received_date':i['received_date'],
        'user':{'name':i['user_name'] or '—','avatar_color':i['user_color'] or '#888'}} for i in rows])

@app.route('/api/incomes', methods=['POST'])
@login_required
def api_add_income():
    d = request.get_json()
    try: dt = datetime.fromisoformat(d.get('received_date', str(date.today()))).date()
    except: dt = date.today()
    iid = run("""INSERT INTO incomes (description,amount,monthly_average,source,user_id,received_date,month,year)
        VALUES (?,?,?,?,?,?,?,?)""",
        (d['description'],float(d['amount']),float(d.get('monthly_average',d['amount'])),
         d.get('source','Salário'),session['user_id'],str(dt),dt.month,dt.year))
    return jsonify({'success':True,'id':iid})

@app.route('/api/incomes/<int:iid>', methods=['DELETE'])
@login_required
def api_delete_income(iid):
    run("DELETE FROM incomes WHERE id=?", (iid,))
    return jsonify({'success':True})

# ── API: Categories ───────────────────────────────────────────────────────────
@app.route('/api/categories')
@login_required
def api_get_categories():
    return jsonify([r2d(c) for c in qry("SELECT * FROM categories ORDER BY is_default DESC, name")])

@app.route('/api/categories', methods=['POST'])
@login_required
def api_add_category():
    d = request.get_json()
    cid = run("INSERT INTO categories (name,icon,color) VALUES (?,?,?)", (d['name'],d.get('icon','💰'),d.get('color','#1D9E75')))
    return jsonify({'success':True,'id':cid})

# ── API: Users ────────────────────────────────────────────────────────────────
@app.route('/api/users')
@login_required
def api_users():
    return jsonify([r2d(u) for u in qry("SELECT id, name, email, avatar_color FROM users")])

# ── API: Monthly Report ───────────────────────────────────────────────────────
@app.route('/api/reports/monthly')
@login_required
def api_monthly_report():
    today = date.today(); results = []
    for i in range(5, -1, -1):
        m, y = today.month - i, today.year
        while m <= 0: m += 12; y -= 1
        inc = qry("SELECT COALESCE(SUM(amount),0) as t FROM incomes WHERE month=? AND year=?", (m,y), one=True)['t']
        exp = qry("SELECT COALESCE(SUM(amount),0) as t FROM transactions WHERE month=? AND year=? AND transaction_type='expense'", (m,y), one=True)['t']
        fixed = qry("SELECT COALESCE(SUM(amount),0) as t FROM fixed_bills WHERE is_active=1", one=True)['t']
        total_exp = exp + fixed
        results.append({'month':m,'year':y,'label':date(y,m,1).strftime('%b/%y'),'income':inc,'expenses':total_exp,'balance':inc-total_exp})
    return jsonify(results)

# ── API: Chat ─────────────────────────────────────────────────────────────────
def fmtBRL(n): return f"R$ {float(n or 0):,.2f}".replace(',','X').replace('.',',').replace('X','.')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    import urllib.request
    d = request.get_json()
    user_msg = d.get('message','')
    history = d.get('history', [])
    today = date.today()
    dash = get_dashboard_data(today.month, today.year)
    user = current_user()
    cat_names = ', '.join(c['name'] for c in qry("SELECT name FROM categories"))

    system = f"""Você é um assistente financeiro pessoal para um casal brasileiro.
Hoje: {today.strftime('%d/%m/%Y')}. Usuário: {user['name'] if user else 'Usuário'}.

DADOS DO MÊS: Renda={fmtBRL(dash['total_income'])}, Gastos={fmtBRL(dash['total_spent'])}, Saldo={fmtBRL(dash['balance'])}, Comprometimento={dash['pct_committed']}%
Categorias: {cat_names}

Quando detectar transação, retorne APENAS JSON sem texto extra:
Gasto: {{"action":"save_transaction","data":{{"description":"...","amount":0.0,"category_name":"...","transaction_type":"expense"}},"message":"confirmação amigável"}}
Receita: {{"action":"save_income","data":{{"description":"...","amount":0.0,"source":"Salário"}},"message":"..."}}
Conta fixa: {{"action":"save_fixed_bill","data":{{"name":"...","amount":0.0,"due_day":1,"category":"Casa","icon":"📄"}},"message":"..."}}
Pergunta: {{"action":"message","message":"resposta em português"}}

Categorias: mercado→Mercado | restaurante/almoço/ifood→Alimentação | gasolina/uber→Transporte | farmácia/médico→Saúde | cinema/viagem→Lazer | aluguel/luz/água/internet→Casa | academia→Saúde | escola/curso→Educação"""

    api_key = os.getenv('ANTHROPIC_API_KEY','')
    if not api_key:
        return jsonify(fallback_chat(user_msg, dash))

    try:
        msgs = [{'role':h['role'],'content':h['content']} for h in history[-6:]]
        msgs.append({'role':'user','content':user_msg})
        payload = json.dumps({'model':'claude-sonnet-4-20250514','max_tokens':600,'system':system,'messages':msgs}).encode()
        req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=payload,
            headers={'Content-Type':'application/json','x-api-key':api_key,'anthropic-version':'2023-06-01'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = json.loads(resp.read())
        text = re.sub(r'```json|```','', raw['content'][0]['text']).strip()
        result = json.loads(text)
    except Exception as e:
        app.logger.error(f"Chat error: {e}")
        return jsonify(fallback_chat(user_msg, dash))

    return jsonify(execute_action(result))

def fallback_chat(msg, dash):
    ml = msg.lower()
    val = re.search(r'(\d+(?:[.,]\d+)?)', ml)
    amount = float(val.group(1).replace(',','.')) if val else 0
    if any(w in ml for w in ['gastei','paguei','comprei','gastamos']) and amount > 0:
        cat = ('Alimentação' if any(w in ml for w in ['mercado','almoço','lanche','restaurante','comida','ifood','pão','leite'])
               else 'Transporte' if any(w in ml for w in ['gasolina','uber','ônibus','combustível','posto'])
               else 'Saúde' if any(w in ml for w in ['farmácia','médico','remédio','consulta'])
               else 'Casa' if any(w in ml for w in ['luz','água','internet','aluguel','conta','gás'])
               else 'Lazer' if any(w in ml for w in ['cinema','pizza','show','restaurante'])
               else 'Outros')
        words = re.sub(r'\d+([.,]\d+)?','', msg).strip()
        desc = ' '.join(w for w in words.split() if w.lower() not in ['gastei','paguei','comprei','reais','r$','hoje','no','na','de','em']).strip().title() or 'Gasto'
        return execute_action({'action':'save_transaction','data':{'description':desc,'amount':amount,'category_name':cat,'transaction_type':'expense'},'message':f'✅ Registrei {fmtBRL(amount)} em {cat}!'})
    if any(w in ml for w in ['recebi','salário','salario']) and amount > 0:
        return execute_action({'action':'save_income','data':{'description':msg.strip().title(),'amount':amount,'source':'Salário'},'message':f'💚 Receita de {fmtBRL(amount)} registrada!'})
    if any(w in ml for w in ['quanto','saldo','gastamos','situação','resumo']):
        return {'action':'message','message':f'📊 Este mês: receberam {fmtBRL(dash["total_income"])}, gastaram {fmtBRL(dash["total_spent"])}, saldo disponível: {fmtBRL(dash["balance"])} ({dash["pct_committed"]}% comprometido).','success':True}
    return {'action':'message','message':'Configure a ANTHROPIC_API_KEY no arquivo .env para o chat inteligente completo. Posso registrar gastos básicos se você disser: "Gastei 50 reais no mercado" 😊','success':True}

def execute_action(result):
    today = date.today()
    if result.get('action') == 'save_transaction':
        d = result['data']
        cat = qry("SELECT id FROM categories WHERE lower(name)=lower(?)", (d.get('category_name','Outros'),), one=True)
        if not cat: cat = qry("SELECT id FROM categories WHERE name='Outros'", one=True)
        cat_id = cat['id'] if cat else None
        run("""INSERT INTO transactions (description,amount,transaction_type,category_id,user_id,transaction_date,notes,month,year)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (d['description'],float(d['amount']),d.get('transaction_type','expense'),
             cat_id,session['user_id'],str(today),'',today.month,today.year))
        result['saved'] = True
    elif result.get('action') == 'save_income':
        d = result['data']
        run("""INSERT INTO incomes (description,amount,monthly_average,source,user_id,received_date,month,year)
            VALUES (?,?,?,?,?,?,?,?)""",
            (d['description'],float(d['amount']),float(d.get('monthly_average',d['amount'])),
             d.get('source','Salário'),session['user_id'],str(today),today.month,today.year))
        result['saved'] = True
    elif result.get('action') == 'save_fixed_bill':
        d = result['data']
        run("INSERT INTO fixed_bills (name,amount,due_day,category,icon,user_id) VALUES (?,?,?,?,?,?)",
            (d['name'],float(d['amount']),int(d.get('due_day',1)),d.get('category','Casa'),d.get('icon','📄'),session['user_id']))
        result['saved'] = True
    result['success'] = True
    return result

# Inicializa o banco sempre (funciona com gunicorn e python app.py)
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

 
 