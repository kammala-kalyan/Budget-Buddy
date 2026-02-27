import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_dev_secret')

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'budgetbuddy'
app.config['MYSQL_PORT'] = 3307
mysql = MySQL(app)

# Decorator to require login
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('page1.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        if not username or not email or not password:
            msg = 'Please fill out all fields.'
        else:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                msg = 'Account already exists!'
            else:
                hashed = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (username, email, password, streak) VALUES (%s, %s, %s, 0)",
                    (username, email, hashed)
                )
                mysql.connection.commit()
                msg = 'You have successfully registered!'
    return render_template('register.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        account = cursor.fetchone()
        if account and check_password_hash(account[3], password):
            session['user_id'] = account[0]
            session['username'] = account[1]
            return redirect(url_for('dashboard'))
        else:
            msg = 'Invalid username or password.'
    return render_template('login.html', msg=msg)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT streak FROM users WHERE id = %s", (user_id,))
    streak = cursor.fetchone()[0] or 0
    return render_template('dashboard.html', streak=streak)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    msg = ''
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    if request.method == 'POST':
        new_email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        if new_email:
            cursor.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
            mysql.connection.commit()
            msg = 'Email updated.'
        if new_password:
            hashed = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, user_id))
            mysql.connection.commit()
            msg += ' Password updated.'
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    email = cursor.fetchone()[0]
    return render_template('profile.html', email=email, msg=msg)

@app.route('/budget-setup', methods=['GET', 'POST'])
@login_required
def budget_setup():
    msg = ''
    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        # 1) Read form inputs
        start_date   = request.form['start_date']
        end_date     = request.form['end_date']
        total_budget = request.form['total_budget']
        cats         = request.form.getlist('category_name')
        percents     = request.form.getlist('category_amount')

        # 2) Validate dates
        try:
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            ed = datetime.datetime.strptime(end_date,   '%Y-%m-%d').date()
            if ed < sd:
                msg = "End date must be after start date."
                return render_template('budget-setup.html', msg=msg)
        except ValueError:
            msg = "Invalid date format."
            return render_template('budget-setup.html', msg=msg)

        # 3) Validate total_budget
        try:
            total_budget = float(total_budget)
        except ValueError:
            msg = "Invalid total budget."
            return render_template('budget-setup.html', msg=msg)

        # 4) Update user streak from last active budget
        cursor.execute("""
            SELECT total_budget, used_budget 
            FROM budgets 
            WHERE user_id = %s AND is_active = TRUE
        """, (user_id,))
        last = cursor.fetchone()
        if last:
            old_total, old_used = last
            cursor.execute("SELECT streak FROM users WHERE id = %s", (user_id,))
            current_streak = cursor.fetchone()[0] or 0
            new_streak = current_streak + 1 if old_used <= old_total else 0
            cursor.execute("UPDATE users SET streak = %s WHERE id = %s", (new_streak, user_id))
            mysql.connection.commit()

        # 5) Deactivate previous budgets
        cursor.execute("UPDATE budgets SET is_active = FALSE WHERE user_id = %s", (user_id,))
        mysql.connection.commit()

        # 6) Create new budget
        cursor.execute(
            "INSERT INTO budgets (user_id, start_date, end_date, total_budget, is_active, used_budget) "
            "VALUES (%s, %s, %s, %s, TRUE, 0)",
            (user_id, start_date, end_date, total_budget)
        )
        mysql.connection.commit()
        budget_id = cursor.lastrowid

        # 7) Validate and insert categories (% → amount)
        total_percent = 0.0
        valid_categories = []
        for cat, pct_str in zip(cats, percents):
            name, pct_s = cat.strip(), pct_str.strip()
            if not name or not pct_s:
                continue
            try:
                pct = float(pct_s)
            except ValueError:
                msg = f"Invalid percentage '{pct_s}' for '{name}'."
                return render_template('budget-setup.html', msg=msg)
            if pct < 0 or pct > 100:
                msg = f"Percentage for '{name}' must be between 0 and 100."
                return render_template('budget-setup.html', msg=msg)
            total_percent += pct
            valid_categories.append((name, pct))

        if total_percent > 100:
            msg = f"Total percentage exceeds 100% ({total_percent}%)."
            return render_template('budget-setup.html', msg=msg)

        leftover = 100 - total_percent

        for name, pct in valid_categories:
            expected_amount = (pct / 100.0) * total_budget
            cursor.execute(
                "INSERT INTO categories (budget_id, name, expected_amount, spent_amount) "
                "VALUES (%s, %s, %s, 0)",
                (budget_id, name, expected_amount)
            )
        mysql.connection.commit()

        # 8) Handle leftover → “Others”
        if leftover > 0:
            others_amt = (leftover / 100.0) * total_budget
            cursor.execute(
                "SELECT id, expected_amount FROM categories "
                "WHERE budget_id = %s AND name = %s",
                (budget_id, 'Others')
            )
            others = cursor.fetchone()
            if others:
                oid, exist_amt = others
                cursor.execute(
                    "UPDATE categories SET expected_amount = %s WHERE id = %s",
                    (exist_amt + others_amt, oid)
                )
            else:
                cursor.execute(
                    "INSERT INTO categories (budget_id, name, expected_amount, spent_amount) "
                    "VALUES (%s, %s, %s, 0)",
                    (budget_id, 'Others', others_amt)
                )
            mysql.connection.commit()

        msg = 'Monthly budget setup complete.'

    return render_template('budget-setup.html', msg=msg)
def get_active_budget_and_categories(user_id, start_date, end_date):
    """Returns (budget_id, [(cat_id, cat_name), …]) or (None, None)."""
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id FROM budgets
         WHERE user_id=%s
           AND is_active=TRUE
           AND start_date<=%s
           AND end_date>=%s
    """, (user_id, end_date, start_date))
    bud = cursor.fetchone()
    if not bud:
        return None, None

    budget_id = bud[0]
    cursor.execute(
        "SELECT id, name FROM categories WHERE budget_id=%s",
        (budget_id,)
    )
    cats = cursor.fetchall()  # list of (id, name)
    return budget_id, cats

@app.route('/add-expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    msg = ''
    uid = session['user_id']

    if request.method == 'POST':
        sd = request.form['start_date']
        ed = request.form['end_date']
        try:
            d_start = datetime.datetime.strptime(sd, '%Y-%m-%d').date()
            d_end   = datetime.datetime.strptime(ed, '%Y-%m-%d').date()
            if d_end < d_start:
                raise ValueError
        except ValueError:
            flash('Invalid date range.')
            return render_template('add-expense.html', categories=[], msg=msg)

        budget_id, categories = get_active_budget_and_categories(uid, sd, ed)
        if not budget_id:
            flash('No budget is set up for those dates.')
            return render_template('add-expense.html', categories=[], msg=msg)
        if not categories:
            flash('No categories defined for that budget.')
            return render_template('add-expense.html', categories=[], msg=msg)

        for cat_id, cat_name in categories:
            amt_str = request.form.get(f'amount_{cat_id}', '').strip()
            note    = request.form.get(f'note_{cat_id}', '').strip()
            if not amt_str:
                continue
            try:
                amount = float(amt_str)
                if amount < 0:
                    raise ValueError
            except ValueError:
                flash(f"Invalid amount for '{cat_name}'.")
                return render_template('add-expense.html', categories=categories, msg=msg)

            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO expenses (user_id, budget_id, category_id, expense_date, amount, note) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (uid, budget_id, cat_id, d_start, amount, note)
            )
            cursor.execute(
                "UPDATE categories SET spent_amount = spent_amount + %s WHERE id = %s",
                (amount, cat_id)
            )
            cursor.execute(
                "UPDATE budgets SET used_budget = used_budget + %s WHERE id = %s",
                (amount, budget_id)
            )

        mysql.connection.commit()
        return redirect(url_for('budget_progress'))

    return render_template('add-expense.html', categories=[], msg=msg)

@app.route('/get-categories', methods=['POST'])
@login_required
def get_categories():
    data = request.get_json()
    sd   = data.get('start_date')
    ed   = data.get('end_date')
    uid  = session['user_id']

    budget_id, categories = get_active_budget_and_categories(uid, sd, ed)
    if not budget_id or not categories:
        return jsonify(success=False, message='No budget found for selected dates.')

    return jsonify(
        success=True,
        categories=[{'id': cid, 'name': name} for cid, name in categories]
    )

@app.route('/budget-progress')
@login_required
def budget_progress():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, total_budget, used_budget FROM budgets WHERE user_id = %s AND is_active = TRUE", (user_id,))
    row = cursor.fetchone()
    if not row:
        return redirect(url_for('budget_setup'))
    budget_id, total, used = row
    cursor.execute("SELECT name, expected_amount, spent_amount FROM categories WHERE budget_id = %s", (budget_id,))
    categories = cursor.fetchall()
    return render_template('budget-progress.html', total=total, used=used, categories=categories)

@app.route('/history')
@login_required
def history():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    # Fetch all budgets (active and archived) with their status
    cursor.execute(
        "SELECT start_date, end_date, total_budget, used_budget, is_active "
        "FROM budgets WHERE user_id = %s ORDER BY start_date DESC",
        (user_id,)
    )
    budgets = cursor.fetchall()  # each row: (start_date, end_date, total_budget, used_budget, is_active)

    return render_template('history.html', budgets=budgets)
@app.route('/reports')
@login_required
def reports():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    # Fetch budgets with their categories in one JOIN
    cursor.execute("""
        SELECT
            b.id AS budget_id,
            b.start_date,
            b.end_date,
            c.name,
            c.expected_amount,
            c.spent_amount
        FROM budgets b
        LEFT JOIN categories c
          ON c.budget_id = b.id
        WHERE b.user_id = %s
        ORDER BY b.start_date DESC, c.id
    """, (user_id,))
    rows = cursor.fetchall()

    # Group rows by budget_id into the format your template expects
    all_reports = []
    current = None
    for bid, sd, ed, cname, exp_amt, spent_amt in rows:
        if current is None or current["budget_id"] != bid:
            current = {
                "budget_id": bid,
                "start_date": sd,
                "end_date": ed,
                "labels": [],
                "expected": [],
                "spent": []
            }
            all_reports.append(current)
        # Only append category data if it exists
        if cname is not None:
            current["labels"].append(cname)
            current["expected"].append(float(exp_amt))
            current["spent"].append(float(spent_amt))

    if not all_reports:
        return render_template("reports.html", all_reports=[], msg="No budget reports found.")

    return render_template("reports.html", all_reports=all_reports, msg="")

@app.route('/monthly-reset', methods=['GET', 'POST'])
@login_required
def monthly_reset():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, total_budget, used_budget FROM budgets WHERE user_id = %s AND is_active = TRUE", (user_id,))
    budget = cursor.fetchone()
    if not budget:
        flash("No active budget found to reset.")
        return render_template('monthly-reset.html', total=0, used=0, no_budget=True)

    budget_id, total, used = budget
    if request.method == 'POST':
        cursor.execute("SELECT streak FROM users WHERE id = %s", (user_id,))
        current = cursor.fetchone()[0] or 0
        new_streak = current + 1 if used <= total else 0
        cursor.execute("UPDATE users SET streak = %s WHERE id = %s", (new_streak, user_id))
        cursor.execute("UPDATE budgets SET is_active = FALSE WHERE id = %s", (budget_id,))
        mysql.connection.commit()
        flash('Budget cycle archived. Streak updated.')
        return redirect(url_for('budget_setup'))
    return render_template('monthly-reset.html', total=total, used=used)
@app.route('/reset-all', methods=['POST'])
@login_required
def reset_all():
    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    # 1) Delete all expenses for this user
    cursor.execute("DELETE FROM expenses WHERE user_id = %s", (user_id,))

    # 2) Delete all categories belonging to this user's budgets
    cursor.execute("""
        DELETE c FROM categories c
        JOIN budgets b ON c.budget_id = b.id
        WHERE b.user_id = %s
    """, (user_id,))

    # 3) Delete all budgets for this user
    cursor.execute("DELETE FROM budgets WHERE user_id = %s", (user_id,))

    # 4) Reset user streak to 0
    cursor.execute("UPDATE users SET streak = 0 WHERE id = %s", (user_id,))

    mysql.connection.commit()
    flash('All budgets, categories, and expenses have been fully reset.')
    return redirect(url_for('budget_setup'))

if __name__ == '__main__':
    app.run(debug=True)
