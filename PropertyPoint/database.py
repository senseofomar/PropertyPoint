import sqlite3
import os

# Absolute Path Logic
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "property_pro_gold.db")

def init_gold_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    curr = conn.cursor()

    # Module 1: Authentication & User Management [cite: 39]
    curr.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE, password TEXT, role TEXT)''')

    # Module 2: Property Management [cite: 43]
    curr.execute('''CREATE TABLE IF NOT EXISTS properties(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    title TEXT, location TEXT, price REAL, 
                    type TEXT, status TEXT, img_url TEXT, owner_id INTEGER)''')

    # Module 4: Booking & Appointment Tracking [cite: 50, 53]
    curr.execute('''CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    buyer_name TEXT, prop_title TEXT, visit_date TEXT, status TEXT)''')

    # Seed demo users for your presentation [cite: 40]
    users = [('admin', 'admin123', 'Admin'),
             ('seller_adi', 'seller123', 'Seller'),
             ('buyer_adi', 'buyer123', 'Buyer')]
    curr.executemany("INSERT OR IGNORE INTO users (username, password, role) VALUES (?,?,?)", users)

    conn.commit()
    conn.close()
    print(f"✅ Gold Database initialized at: {DB_PATH}")

if __name__ == "__main__":
    init_gold_db()