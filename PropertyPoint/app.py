from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configuration for Image Uploads
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, location TEXT, price INTEGER, type TEXT, owner TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, buyer TEXT, property_title TEXT, status TEXT)")

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ('admin', generate_password_hash('admin123'), 'Admin'))

    if cur.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == 0:
        cities = ["Mumbai", "Pune", "Latur", "Hyderabad", "Nagpur", "Delhi", "Bangalore", "Chennai"]
        types = ["Villa", "Apartment", "Commercial Office", "Plot", "Penthouse", "Farmhouse"]
        for i in range(50):
            city, ptype = random.choice(cities), random.choice(types)
            price = random.randint(1000000, 20000000)
            cur.execute("INSERT INTO properties (title, location, price, type, owner) VALUES (?, ?, ?, ?, ?)",
                        (f"Premium {ptype} in {city}", city, price, ptype, "system"))
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username, password, role = request.form["username"], request.form["password"], request.form["role"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND role=?", (username, role)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session["user"], session["role"] = username, role
            return redirect(f"/{role.lower()}")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username, pw, role = request.form["username"], request.form["password"], request.form["role"]
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, generate_password_hash(pw), role))
            conn.commit()
            return redirect("/")
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists")
        finally:
            conn.close()
    return render_template("signup.html")

@app.route("/book/<int:property_id>", methods=["POST"])
def book(property_id):
    if session.get("role", "").lower() != "buyer":
        return jsonify({"success": False, "error": "Only buyers can book visits"}), 403
    conn = get_db()
    prop = conn.execute("SELECT title FROM properties WHERE id=?", (property_id,)).fetchone()
    if prop:
        conn.execute("INSERT INTO bookings (buyer, property_title, status) VALUES (?, ?, ?)",
                     (session["user"], prop[0], "Pending"))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    conn.close()
    return jsonify({"success": False, "error": "Property not found"}), 404

@app.route("/admin")
def admin():
    if session.get("role") != "Admin": return redirect("/")
    conn = get_db()
    users_list = conn.execute("SELECT * FROM users").fetchall()
    properties = conn.execute("SELECT * FROM properties").fetchall()
    bookings = conn.execute("SELECT * FROM bookings").fetchall()
    stats = {
        "u_count": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "p_count": conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0],
        "b_count": conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    }
    conn.close()
    return render_template("admin.html", users=users_list, properties=properties, bookings=bookings, **stats)

@app.route("/admin/approve/<int:booking_id>")
def approve(booking_id):
    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'Approved' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_status": "Approved"})

@app.route("/admin/reject/<int:booking_id>")
def reject(booking_id):
    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'Rejected' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_status": "Rejected"})

@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "Admin": return jsonify({"success": False}), 403
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/seller", methods=["GET", "POST"])
def seller():
    if session.get("role") != "Seller": return redirect("/")
    conn = get_db()
    if request.method == "POST":
        title, loc, price, ptype = request.form["title"], request.form["location"], request.form["price"], request.form[
            "type"]
        file = request.files.get('image')
        img_filename = ""
        if file:
            img_filename = f"prop_{random.randint(1000, 9999)}.jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))

        conn.execute("INSERT INTO properties (title, location, price, type, owner, img_url) VALUES (?,?,?,?,?,?)",
                     (title, loc, price, ptype, session["user"], img_filename))
        conn.commit()

    properties = conn.execute("SELECT * FROM properties WHERE owner=?", (session["user"],)).fetchall()
    conn.close()
    return render_template("seller.html", properties=properties)


@app.route("/buyer")
def buyer():
    if session.get("role") != "Buyer": return redirect("/")
    conn = get_db()
    # Now retrieves ALL properties (System generated + Seller listed)
    properties = conn.execute("SELECT * FROM properties ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("buyer.html", properties=properties)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)