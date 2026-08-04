import sqlite3
import sys
import csv
from datetime import datetime

DB_NAME = "expense_tracker.db"

def init_db():
    """Creates the relational schema with three required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            monthly_budget REAL DEFAULT 0.0
        )
    ''')
    
    # 2. Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # 3. Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')
    
    # Pre-populate required categories from screenshot guidelines
    default_categories = ['Food', 'Transport', 'Utilities', 'Entertainment', 'Other']
    for cat in default_categories:
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
        
    conn.commit()
    conn.close()

# --- Authentication Module ---
def auth_menu():
    init_db()
    while True:
        print("\n===== PERSONAL EXPENSE TRACKER =====")
        print("1. Login to Existing Account")
        print("2. Register New Account")
        print("3. Exit System")
        
        choice = input("Enter choice (1-3): ").strip()
        if choice == '1':
            user = login_user()
            if user:
                user_dashboard(user)
        elif choice == '2':
            register_user()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid selection.")

def register_user():
    username = input("Create a unique username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return
    try:
        budget = float(input("Set your overall monthly budget limit (Rs.): "))
    except ValueError:
        budget = 0.0

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, monthly_budget) VALUES (?, ?)", (username, budget))
        conn.commit()
        print(f"Account '{username}' registered successfully!")
    except sqlite3.IntegrityError:
        print("Error: That username is already taken.")
    finally:
        conn.close()

def login_user():
    username = input("Enter your username: ").strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, monthly_budget FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        print(f"\nWelcome back, {user[1]}!")
        return {"id": user[0], "username": user[1], "budget": user[2]}
    print("User profile not found. Please register first.")
    return None

# --- Core Features Module ---
def record_expense(user):
    print("\n--- Record an Expense ---")
    current_month = datetime.now().strftime("%Y-%m")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # --- BEFORE EXPENDITURE ANALYSIS ---
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND date LIKE ?
    ''', (user["id"], f"{current_month}%"))
    spent_before = cursor.fetchone()[0] or 0.0
    budget_before = user["budget"] - spent_before
    
    print(f"Current Monthly Budget Remaining: Rs.{budget_before:.2f}")
    print("-" * 40)
    
    # Select category relational key
    cursor.execute("SELECT id, name FROM categories")
    cats = cursor.fetchall()
    print("Available Expense Categories:")
    for row in cats:
        print(f"  {row[0]}. {row[1]}")
        
    try:
        cat_choice = int(input("Select category item ID: "))
        if cat_choice not in [r[0] for r in cats]:
            print("Invalid category selected.")
            conn.close()
            return
    except ValueError:
        conn.close()
        return

    try:
        amount = float(input("Enter spending amount (Rs.): "))
        if amount <= 0: 
            conn.close()
            return
    except ValueError:
        print("Invalid number input.")
        conn.close()
        return

    date = input("Enter execution date (YYYY-MM-DD) [Press Enter for today]: ").strip()
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    desc = input("Provide descriptive reference details: ").strip()

    # Save to database
    cursor.execute('''
        INSERT INTO expenses (user_id, category_id, amount, date, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (user["id"], cat_choice, amount, date, desc if desc else "N/A"))
    conn.commit()
    
    # --- AFTER EXPENDITURE ANALYSIS ---
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND date LIKE ?
    ''', (user["id"], f"{current_month}%"))
    spent_after = cursor.fetchone()[0] or 0.0
    budget_after = user["budget"] - spent_after
    
    conn.close()
    
    print("\n========================================")
    print(" Expense Recorded Successfully!")
    print(f" Budget Remaining BEFORE: Rs.{budget_before:.2f}")
    print(f" Amount Deducted:        Rs.{amount:.2f}")
    print(f" Budget Remaining AFTER:  Rs.{budget_after:.2f}")
    
    if budget_after < 0:
        print(" ALERT: You have exceeded your monthly budget cap limit!")
    print("========================================")

def view_monthly_summary(user):
    """Uses SUM() aggregation to track spending relative to user budget constraints."""
    print("\n--- Monthly Budget Tracker Status ---")
    current_month = datetime.now().strftime("%Y-%m")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(amount) FROM expenses 
        WHERE user_id = ? AND date LIKE ?
    ''', (user["id"], f"{current_month}%"))
    
    total_spent = cursor.fetchone()[0] or 0.0
    conn.close()
    
    remaining_balance = user['budget'] - total_spent
    
    print(f"Target Tracked Month: {current_month}")
    print(f"Configured Budget Cap: Rs.{user['budget']:.2f}")
    print(f"Aggregated Spending:   Rs.{total_spent:.2f}")
    print(f"Net Available Balance: Rs.{remaining_balance:.2f}")
    
    if total_spent > user['budget']:
        print("  ALERT: You have exceeded your allocated budget target parameters!")
    else:
        print(" Safe: Your expenditure patterns remain inside designated safety limits.")

def search_by_category(user):
    category_name = input("\nEnter category label to search (e.g., Food, Transport): ").strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.date, c.name, e.amount, e.description 
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ? AND c.name LIKE ?
        ORDER BY e.date DESC
    ''', (user["id"], f"%{category_name}%"))
    display_rows(cursor.fetchall())
    conn.close()

def search_by_date_range(user):
    print("\nEnter Date Range boundaries (Format: YYYY-MM-DD)")
    start = input("Start Date: ").strip()
    end = input("End Date: ").strip()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.date, c.name, e.amount, e.description 
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ? AND e.date BETWEEN ? AND ?
        ORDER BY e.date DESC
    ''', (user["id"], start, end))
    display_rows(cursor.fetchall())
    conn.close()

def view_advanced_insights(user):
    """Fulfills tech stack constraints utilizing AVG(), SUM(), and GROUP BY clusters."""
    print("\n--- Analytical Metric Breakdowns ---")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Total and Average Spending Per Category (Uses SUM, AVG, GROUP BY)
    cursor.execute('''
        SELECT c.name, SUM(e.amount), AVG(e.amount)
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
        GROUP BY c.name
    ''', (user["id"],))
    insights = cursor.fetchall()
    
    if not insights:
        print("Insufficient database information recorded to structure analytics metrics.")
        conn.close()
        return
        
    print(f"{'Category':<15} | {'Total Volume':<15} | {'Average Transaction'}")
    print("-" * 55)
    for row in insights:
        print(f"{row[0]:<15} | Rs.{row[1]:<14.2f} | Rs.{row[2]:<14.2f}")
    conn.close()

def export_reports_csv(user):
    """Exports personal logs into physical CSV worksheets files."""
    filename = f"User_{user['username']}_Expense_Report.csv"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.date, c.name, e.amount, e.description 
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ? ORDER BY e.date DESC
    ''', (user["id"],))
    records = cursor.fetchall()
    conn.close()
    
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Category', 'Amount (Rs.)', 'Description'])
        writer.writerows(records)
        
    print(f"Report exported successfully! Saved to directory folder as: '{filename}'")

def display_rows(records):
    if not records:
        print("No matches tracked inside query lookups.")
        return
    print(f"\n{'ID':<5} | {'Date':<12} | {'Category':<15} | {'Amount':<10} | {'Description'}")
    print("-" * 75)
    for row in records:
        print(f"{row[0]:<5} | {row[1]:<12} | {row[2]:<15} | Rs.{row[3]:<9.2f} | {row[4]}")

# --- Primary User Session Loop ---
def user_dashboard(user):
    while True:
        print(f"\n===== DASHBOARD ({user['username'].upper()}) =====")
        print("1. Record New Expense Item")
        print("2. Check Monthly Spending Summary & Budget")
        print("3. Filter History by Category Group")
        print("4. Filter History by Date Range Range")
        print("5. Run Analytics Performance Insights (AVG/SUM)")
        print("6. Export Ledger to CSV Report Sheet")
        print("7. Logout Account")
        
        choice = input("Select Workspace Action (1-7): ").strip()
        if choice == '1': record_expense(user)
        elif choice == '2': view_monthly_summary(user)
        elif choice == '3': search_by_category(user)
        elif choice == '4': search_by_date_range(user)
        elif choice == '5': view_advanced_insights(user)
        elif choice == '6': export_reports_csv(user)
        elif choice == '7': 
            print("Session closed successfully.")
            break
        else:
            print("Invalid code matrix parameter selection.")

if __name__ == "__main__":
    auth_menu()
    