<h1 align="center">📘 Budget Buddy – Personal Money Management Web App</h1>

<p align="center">
  Budget Buddy is a full-stack web application built using <b>Flask (Python)</b> and <b>MySQL</b> 
  to help users plan monthly budgets, track expenses, and view spending insights.
</p>

<hr>

<h2>🚀 Features</h2>

<ul>
  <li><b>User Authentication</b> – Secure login & registration</li>
  <li><b>Monthly Budget Planning</b> – Create budgets with custom categories</li>
  <li><b>Expense Tracking</b> – Add expenses with real-time updates</li>
  <li><b>Dashboard Overview</b> – View progress bars & spending summary</li>
  <li><b>Financial Streak</b> – Track how many months you stayed under budget</li>
  <li><b>Reports & History</b> – Visual insights and past budget data</li>
  <li><b>Auto Monthly Reset</b> – Automatically start a new cycle</li>
</ul>

<hr>

<h2>🏗️ System Architecture</h2>

<pre>
Client (Browser)
    ↓
Flask Web Server (Python)
    ↓
MySQL Database
</pre>

<h3>Frontend</h3>
<ul>
  <li>HTML, CSS, JavaScript</li>
  <li>Jinja2 templating</li>
</ul>

<h3>Backend</h3>
<ul>
  <li>Python (Flask)</li>
  <li>Budget Logic, Authentication, Expense APIs</li>
</ul>

<h3>Database</h3>
<ul>
  <li>MySQL (Normalized to 3NF)</li>
  <li>Tables: users, budgets, categories, expenses</li>
</ul>

<hr>

<h2>🗂️ Project Folder Structure</h2>

<pre>
Budget Buddy/
│
├── app.py
├── static/
│   ├── style.css
│   ├── script.js
│   └── *.png
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── budget-setup.html
│   ├── add-expense.html
│   ├── budget-progress.html
│   ├── history.html
│   ├── reports.html
│   └── setup.html
│
├── venv/            (ignored)
└── __pycache__/     (ignored)
</pre>

<hr>

<h2>🛢️ Database Schema Overview</h2>

<h3>1. users</h3>
<ul>
  <li>id (PK)</li>
  <li>username</li>
  <li>email</li>
  <li>password</li>
  <li>streak</li>
</ul>

<h3>2. budgets</h3>
<ul>
  <li>id (PK)</li>
  <li>user_id (FK)</li>
  <li>start_date / end_date</li>
  <li>total_budget</li>
  <li>used_budget</li>
  <li>is_active</li>
</ul>

<h3>3. categories</h3>
<ul>
  <li>id (PK)</li>
  <li>budget_id (FK)</li>
  <li>name</li>
  <li>expected_amount</li>
  <li>spent_amount</li>
</ul>

<h3>4. expenses</h3>
<ul>
  <li>id (PK)</li>
  <li>user_id (FK)</li>
  <li>budget_id (FK)</li>
  <li>category_id (FK)</li>
  <li>expense_date</li>
  <li>amount</li>
  <li>note</li>
</ul>

<hr>

<h2>⚙️ Setup Instructions</h2>

<h3>1️⃣ Install Dependencies</h3>
<pre>
pip install flask flask_mysqldb
</pre>
