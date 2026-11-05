from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key-for-your-own-deployment"
DB_PATH = Path(__file__).with_name("bank.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT UNIQUE NOT NULL,
                holder_name TEXT NOT NULL,
                email TEXT,
                account_type TEXT NOT NULL DEFAULT 'Savings',
                balance_paise INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                related_account_id INTEGER,
                transaction_type TEXT NOT NULL,
                amount_paise INTEGER NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id),
                FOREIGN KEY(related_account_id) REFERENCES accounts(id)
            )
        """)


def money_to_paise(raw):
    try:
        value = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if value <= 0:
            raise ValueError("Amount must be greater than zero.")
        return int(value * 100)
    except (InvalidOperation, TypeError):
        raise ValueError("Enter a valid amount.")


def fmt(paise):
    return f"₹{(int(paise or 0) / 100):,.2f}"


app.jinja_env.filters["inr"] = fmt


def make_account_number():
    with db() as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 100000) + 1 AS n FROM accounts").fetchone()
        return f"SBIN{row['n']:06d}"


@app.route("/")
def dashboard():
    with db() as conn:
        accounts = conn.execute("SELECT * FROM accounts ORDER BY id DESC").fetchall()
        total_balance = conn.execute("SELECT COALESCE(SUM(balance_paise),0) AS total FROM accounts").fetchone()["total"]
        tx_count = conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
        recent = conn.execute("""
            SELECT t.*, a.account_number, a.holder_name,
                   r.account_number AS related_number
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            LEFT JOIN accounts r ON r.id = t.related_account_id
            ORDER BY t.id DESC LIMIT 8
        """).fetchall()
    return render_template("index.html", accounts=accounts, total_balance=total_balance,
                           tx_count=tx_count, recent=recent)


@app.post("/accounts/create")
def create_account():
    name = request.form.get("holder_name", "").strip()
    email = request.form.get("email", "").strip()
    account_type = request.form.get("account_type", "Savings")
    if not name:
        flash("Please enter the account holder's name.", "error")
        return redirect(url_for("dashboard"))
    if account_type not in ("Savings", "Current"):
        account_type = "Savings"
    number = make_account_number()
    with db() as conn:
        conn.execute("""
            INSERT INTO accounts(account_number, holder_name, email, account_type, balance_paise, created_at)
            VALUES(?,?,?,?,0,?)
        """, (number, name, email, account_type, datetime.now().isoformat(timespec="seconds")))
    flash(f"Account {number} created successfully.", "success")
    return redirect(url_for("dashboard"))


@app.post("/transactions/credit")
def credit():
    account_id = request.form.get("account_id", type=int)
    try:
        amount = money_to_paise(request.form.get("amount", ""))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    with db() as conn:
        account = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not account:
            flash("Select a valid account.", "error")
        else:
            conn.execute("UPDATE accounts SET balance_paise=balance_paise+? WHERE id=?", (amount, account_id))
            conn.execute("""
                INSERT INTO transactions(account_id, transaction_type, amount_paise, description, created_at)
                VALUES(?,?,?,?,?)
            """, (account_id, "Credit", amount, "Cash deposit", datetime.now().isoformat(timespec="seconds")))
            flash(f"{fmt(amount)} credited to {account['account_number']}.", "success")
    return redirect(url_for("dashboard"))


@app.post("/transactions/debit")
def debit():
    account_id = request.form.get("account_id", type=int)
    try:
        amount = money_to_paise(request.form.get("amount", ""))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    with db() as conn:
        account = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not account:
            flash("Select a valid account.", "error")
        elif account["balance_paise"] < amount:
            flash("Insufficient balance. Withdrawal was not processed.", "error")
        else:
            conn.execute("UPDATE accounts SET balance_paise=balance_paise-? WHERE id=?", (amount, account_id))
            conn.execute("""
                INSERT INTO transactions(account_id, transaction_type, amount_paise, description, created_at)
                VALUES(?,?,?,?,?)
            """, (account_id, "Debit", amount, "Cash withdrawal", datetime.now().isoformat(timespec="seconds")))
            flash(f"{fmt(amount)} debited from {account['account_number']}.", "success")
    return redirect(url_for("dashboard"))


@app.post("/transactions/transfer")
def transfer():
    from_id = request.form.get("from_account", type=int)
    to_id = request.form.get("to_account", type=int)
    try:
        amount = money_to_paise(request.form.get("amount", ""))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    with db() as conn:
        source = conn.execute("SELECT * FROM accounts WHERE id=?", (from_id,)).fetchone()
        target = conn.execute("SELECT * FROM accounts WHERE id=?", (to_id,)).fetchone()
        if not source or not target:
            flash("Choose valid source and destination accounts.", "error")
        elif from_id == to_id:
            flash("Source and destination accounts must be different.", "error")
        elif source["balance_paise"] < amount:
            flash("Insufficient balance. Transfer was not processed.", "error")
        else:
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute("UPDATE accounts SET balance_paise=balance_paise-? WHERE id=?", (amount, from_id))
            conn.execute("UPDATE accounts SET balance_paise=balance_paise+? WHERE id=?", (amount, to_id))
            conn.execute("""
                INSERT INTO transactions(account_id, related_account_id, transaction_type, amount_paise, description, created_at)
                VALUES(?,?,?,?,?,?)
            """, (from_id, to_id, "Transfer Out", amount, f"Transferred to {target['account_number']}", now))
            conn.execute("""
                INSERT INTO transactions(account_id, related_account_id, transaction_type, amount_paise, description, created_at)
                VALUES(?,?,?,?,?,?)
            """, (to_id, from_id, "Transfer In", amount, f"Received from {source['account_number']}", now))
            flash(f"{fmt(amount)} transferred successfully to {target['account_number']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/history")
def history():
    account_id = request.args.get("account_id", type=int)
    with db() as conn:
        accounts = conn.execute("SELECT * FROM accounts ORDER BY holder_name").fetchall()
        query = """
            SELECT t.*, a.account_number, a.holder_name,
                   r.account_number AS related_number
            FROM transactions t
            JOIN accounts a ON a.id=t.account_id
            LEFT JOIN accounts r ON r.id=t.related_account_id
        """
        params = ()
        if account_id:
            query += " WHERE t.account_id=?"
            params = (account_id,)
        query += " ORDER BY t.id DESC"
        transactions = conn.execute(query, params).fetchall()
    return render_template("history.html", accounts=accounts, transactions=transactions, selected=account_id)


@app.route("/accounts/<int:account_id>")
def account_detail(account_id):
    with db() as conn:
        account = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        transactions = conn.execute("""
            SELECT t.*, r.account_number AS related_number
            FROM transactions t LEFT JOIN accounts r ON r.id=t.related_account_id
            WHERE t.account_id=? ORDER BY t.id DESC
        """, (account_id,)).fetchall()
    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("dashboard"))
    return render_template("account.html", account=account, transactions=transactions)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
