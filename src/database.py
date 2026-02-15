import sqlite3
import random


def init_db():
    conn = sqlite3.connect('real_estate.db', check_same_thread=False)
    curr = conn.cursor()
    curr.execute("DROP TABLE IF EXISTS properties")
    curr.execute('''CREATE TABLE IF NOT EXISTS properties
                    (
                        id
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        title
                        TEXT,
                        location
                        TEXT,
                        price
                        REAL,
                        bhk
                        INTEGER,
                        type
                        TEXT,
                        status
                        TEXT,
                        img_url
                        TEXT,
                        description
                        TEXT
                    )''')

    locations = ["Ausa Road", "MIDC", "Latur Central", "Puranmal Nagar", "Signal Camp"]
    types = ["Flat", "Villa", "Row House", "Studio"]

    properties = []
    for i in range(50):
        p_type = random.choice(types)
        loc = random.choice(locations)
        # Fix: Using unique 'sig' parameter for each image to prevent recurring photos
        img_id = random.randint(1, 1000)
        img_url = f"https://picsum.photos/seed/{img_id}/800/600"

        properties.append((
            f"{random.randint(1, 5)} BHK {p_type}",
            loc,
            random.randint(25, 200) * 100000,
            random.randint(1, 5),
            p_type,
            "Available",
            img_url,
            f"Premium {p_type} with modern interior and excellent ventilation."
        ))

    curr.executemany(
        "INSERT INTO properties (title, location, price, bhk, type, status, img_url, description) VALUES (?,?,?,?,?,?,?,?)", properties)
    conn.commit()
    conn.close()
    print("Database Refreshed: 50 Unique Properties Created.")

if __name__ == "__main__":
    init_db()