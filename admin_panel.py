from flask import Flask, render_template_string, request, redirect
import json
import os
import re
import requests

from flask import session, redirect, url_for, flash
app = Flask(__name__)
app.secret_key = 'change_this_secret_key'  # Change this to a random secret in production

# Set your admin password here
ADMIN_PASSWORD = 'admin123'  # Change this to a strong password

INVENTORY_FILE = "codes.json"
PENDING_FILE = "pending_payments.json"
ADMIN_CONFIG = "admin_config.json"

# Try load bot token from env or from tg_bot.py
def load_bot_token():
    token = os.environ.get("BOT_TOKEN")
    if token:
        return token
    # try to read from tg_bot.py
    tg_path = os.path.join(os.path.dirname(__file__), "tg_bot.py")
    if os.path.exists(tg_path):
        with open(tg_path, "r", encoding="utf8") as f:
            content = f.read()
        m = re.search(r'BOT_TOKEN\s*=\s*["\'](.+?)["\']', content)
        if m:
            return m.group(1)
    return None

BOT_TOKEN = load_bot_token()

def load_admin_config():
    if not os.path.exists(ADMIN_CONFIG):
        # default admin mobile (India) — change as needed
        return {"admin_mobile": "7575025625"}
    with open(ADMIN_CONFIG, "r") as f:
        return json.load(f)

def save_admin_config(cfg):
    with open(ADMIN_CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)

# Load inventory

def load_inventory():
    if not os.path.exists(INVENTORY_FILE):
        return {}
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)

def save_inventory(inv):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inv, f, indent=2)

# Load pending payments

def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE, "r") as f:
        return json.load(f)

def save_pending(pending):
    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            flash("Incorrect password!", "danger")
    return render_template_string('''
        <h2>Admin Login</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <ul>
            {% for category, message in messages %}
              <li style="color:red">{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <form method="post">
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    ''')

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    pending = load_pending()
    inventory = load_inventory()
    cfg = load_admin_config()
    return render_template_string('''
    <a href="/logout">Logout</a>
    <h2>Admin Mobile: {{ cfg.admin_mobile }}</h2>
    <form method="post" action="/set_admin_mobile">
        <input name="admin_mobile" placeholder="Admin mobile" value="{{ cfg.admin_mobile }}">
        <button type="submit">Save</button>
    </form>
    <h2>Pending Payment Requests</h2>
    <table border="1">
        <tr><th>User ID</th><th>Username</th><th>Item</th><th>Buyer Mobile</th><th>Actions</th></tr>
        {% for req in pending %}
        <tr>
            <td>{{ req['user_id'] }}</td>
            <td>{{ req['username'] or req['user_id'] }}</td>
            <td>{{ req['item_id'] }}</td>
            <td>
                <form method="post" action="/update_buyer_mobile" style="display:inline">
                    <input type="hidden" name="user_id" value="{{ req['user_id'] }}">
                    <input type="text" name="buyer_mobile" placeholder="Mobile" value="{{ req.get('buyer_mobile','') }}">
                    <button type="submit">Save</button>
                </form>
                {% if req.get('buyer_mobile') %}
                    <a href="tel:{{ req['buyer_mobile'] }}">Call</a>
                {% endif %}
            </td>
            <td>
                <form method="post" action="/grant" style="display:inline">
                    <input type="hidden" name="user_id" value="{{ req['user_id'] }}">
                    <input type="hidden" name="item_id" value="{{ req['item_id'] }}">
                    <button type="submit">Grant Code</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
    <h2>Inventory</h2>
    <pre>{{ inventory | tojson(indent=2) }}</pre>
    ''', pending=pending, inventory=inventory, cfg=cfg)


@app.route('/set_admin_mobile', methods=['POST'])
def set_admin_mobile():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    admin_mobile = request.form.get('admin_mobile','').strip()
    cfg = load_admin_config()
    cfg['admin_mobile'] = admin_mobile
    save_admin_config(cfg)
    return redirect(url_for('index'))


@app.route('/update_buyer_mobile', methods=['POST'])
def update_buyer_mobile():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    user_id = request.form.get('user_id')
    mobile = request.form.get('buyer_mobile','').strip()
    pending = load_pending()
    updated = False
    for req in pending:
        if str(req.get('user_id')) == str(user_id):
            req['buyer_mobile'] = mobile
            updated = True
            break
    if updated:
        save_pending(pending)
    return redirect(url_for('index'))

@app.route("/grant", methods=["POST"])
def grant_code():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    user_id = request.form["user_id"]
    item_id = request.form["item_id"]
    inventory = load_inventory()
    codes = inventory.get(item_id, [])
    if not codes:
        return "No codes left for this item! <a href='/'>Back</a>"
    code = codes.pop(0)
    inventory[item_id] = codes
    save_inventory(inventory)
    # Remove from pending
    pending = load_pending()
    pending = [req for req in pending if not (str(req['user_id']) == str(user_id) and req['item_id'] == item_id)]
    save_pending(pending)
    # Send code to user via Telegram (if token available)
    sent = False
    error_text = None
    if BOT_TOKEN:
        try:
            send_text = (
                "✅ Payment confirmed!\n\n"
                f"Here is your code:\n```\n{code}\n```\n\n"
                "Thank you for your purchase 🎉"
            )
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": int(user_id), "text": send_text, "parse_mode": "Markdown"}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                sent = True
            else:
                error_text = f"Telegram API error: {r.status_code} {r.text}"
        except Exception as e:
            error_text = str(e)

    # Return admin view
    if sent:
        return f"Code granted and sent: <b>{code}</b> to user {user_id}. <a href='/'>Back</a>"
    else:
        note = " (NOT sent automatically; configure BOT_TOKEN)" if not BOT_TOKEN else f" (send error: {error_text})"
        return f"Code granted: <b>{code}</b> for user {user_id}.{note} <a href='/'>Back</a>"

if __name__ == "__main__":
    app.run(debug=True)
