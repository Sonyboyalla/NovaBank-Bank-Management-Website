# NovaBank – Bank Management Website

A local banking-management practice project built with Python Flask, SQLite, HTML, CSS and JavaScript.

## Features
- Create Savings and Current accounts
- Credit / deposit money
- Debit / withdraw money
- Transfer money between two different accounts
- Account balance overview and account details
- Transaction history with account filters
- Persistent SQLite storage (`bank.db`)
- Input validation and insufficient-balance protection

## Run on Windows
1. Install Python 3.10 or newer.
2. Open PowerShell or Command Prompt in this project folder.
3. Create and activate a virtual environment (recommended):

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Start the website:

   ```powershell
   python app.py
   ```

6. Open http://127.0.0.1:5000 in your browser.

## Try the requested workflow
1. Create account one (for example, "Sony Boyalla").
2. Create account two (for example, "Test User").
3. In Credit Money, choose account one and enter `5000`.
4. In Debit Money, choose account one and enter `1000`.
5. In Transfer Money, choose account one as From, account two as To, and enter `500`.
6. Open Transactions to see the credit, debit, transfer-out and transfer-in records.

After these operations, account one has ₹3,500 and account two has ₹500, assuming both accounts started at ₹0.

## Database
The SQLite database is created automatically as `bank.db` when the app starts. Do not delete it if you want to keep your practice data.

## Important
This is an educational demo application, not a real banking system. It does not connect to banks or move real money. Before any public deployment, add proper authentication, authorization, CSRF protection, secure secret management, audit controls, HTTPS and production hosting configuration.
