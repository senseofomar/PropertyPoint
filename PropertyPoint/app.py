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
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, location TEXT, price INTEGER, type TEXT, owner TEXT, img_url TEXT, description TEXT)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, buyer TEXT, property_title TEXT, status TEXT)")

    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ('admin', generate_password_hash('admin123'), 'Admin'))

    if cur.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == 0:
        cities = ["Mumbai", "Pune", "Latur", "Hyderabad", "Nagpur", "Delhi", "Bangalore", "Chennai"]
        types = ["Villa", "Apartment", "Commercial Office", "Plot", "Penthouse", "Farmhouse"]

        # New dynamic vocabulary
        adjectives = ["Exquisite", "Luxurious", "Modern", "Spacious", "Elegant", "Premium", "Ultra-luxury"]
        features = {
            "Villa": ["a private pool, landscaped gardens, and smart home automation.",
                      "breathtaking views, high ceilings, and a state-of-the-art kitchen."],
            "Apartment": ["24/7 security, an infinity pool, and premium clubhouse access.",
                          "panoramic city views, imported marble flooring, and concierge service."],
            "Commercial Office": ["high-speed elevators, ample parking, and prime main-road visibility.",
                                  "grade-A infrastructure, cafeteria space, and 100% power backup."],
            "Plot": ["clear titles, excellent road connectivity, and high appreciation potential.",
                     "a serene environment, gated security, and proximity to upcoming tech hubs."],
            "Penthouse": ["a private terrace, floor-to-ceiling windows, and exclusive elevator access.",
                          "unmatched luxury, an open-concept layout, and a private jacuzzi."],
            "Farmhouse": ["lush greenery, organic fruit orchards, and a cozy outhouse.",
                          "sprawling acres of land, a private lake, and rustic luxury architecture."]
        }

        for i in range(50):
            city, ptype = random.choice(cities), random.choice(types)
            price = random.randint(1000000, 20000000)

            # Generate the dynamic description
            adj = random.choice(adjectives)
            feat = random.choice(features[ptype])
            dynamic_desc = f"This {adj.lower()} {ptype.lower()} is located in the highly sought-after area of {city}. It features {feat} Perfect for discerning buyers looking for a high-quality lifestyle."

            cur.execute(
                "INSERT INTO properties (title, location, price, type, owner, img_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"{adj} {ptype} in {city}", city, price, ptype, "system", "", dynamic_desc))
    conn.commit()
    conn.close()

init_db()

# --- AUTHENTICATION ROUTES ---
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
        username = request.form["username"]
        pw = request.form["password"]
        confirm_pw = request.form.get("confirm_password") # NEW
        role = request.form["role"]

        # Backend validation for matching passwords
        if pw != confirm_pw:
            return render_template("signup.html", error="Passwords do not match. Please try again.")

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, generate_password_hash(pw), role))
            conn.commit()
            flash("Account created successfully! Please log in.")
            return redirect("/")
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists")
        finally:
            conn.close()
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/admin-portal", methods=["GET", "POST"])
def admin_portal():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        # Hardcode the role check to 'Admin' for security
        user = conn.execute("SELECT * FROM users WHERE username=? AND role='Admin'", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session["user"] = username
            session["role"] = "Admin"
            return redirect("/admin")

        return render_template("admin_login.html", error="Authentication failed.")

    return render_template("admin_login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user:
            # Update the user's password with a new hash
            conn.execute("UPDATE users SET password=? WHERE username=?",
                         (generate_password_hash(new_password), username))
            conn.commit()
            conn.close()

            flash("Password reset successfully! Please log in with your new password.")
            return redirect("/")
        else:
            conn.close()
            return render_template("forgot_password.html", error="Username not found in our system.")

    return render_template("forgot_password.html")

# --- BUYER ROUTES ---
@app.route("/buyer")
def buyer():
    if session.get("role") != "Buyer": return redirect("/")

    city_query = request.args.get('city', '')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)

    conn = get_db()
    query = "SELECT * FROM properties WHERE 1=1"
    params = []

    if city_query:
        query += " AND location LIKE ?"
        params.append('%' + city_query + '%')
    if min_price:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY id DESC"
    properties = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("buyer.html", properties=properties, search_term=city_query, min_price=min_price, max_price=max_price)

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


@app.route("/my_bookings")
def my_bookings():
    if session.get("role") != "Buyer": return redirect("/")
    conn = get_db()
    user_bookings = conn.execute("SELECT * FROM bookings WHERE buyer = ?", (session["user"],)).fetchall()
    conn.close()
    return render_template("my_bookings.html", bookings=user_bookings)


# --- SELLER ROUTES ---
@app.route("/seller", methods=["GET", "POST"])
def seller():
    if session.get("role") != "Seller": return redirect("/")
    conn = get_db()
    if request.method == "POST":
        title, loc, price, ptype = request.form["title"], request.form["location"], request.form["price"], request.form[
            "type"]
        description = request.form.get("description", "No description provided.")  # NEW

        file = request.files.get('image')
        img_filename = ""
        if file and file.filename != '':
            img_filename = f"prop_{random.randint(1000, 9999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))

        # ADDED description to the INSERT statement
        conn.execute(
            "INSERT INTO properties (title, location, price, type, owner, img_url, description) VALUES (?,?,?,?,?,?,?)",
            (title, loc, price, ptype, session["user"], img_filename, description))
        conn.commit()
        flash("Congratulations! Your property is now live and visible to buyers.")

    properties = conn.execute("SELECT * FROM properties WHERE owner=?", (session["user"],)).fetchall()
    conn.close()
    return render_template("seller.html", properties=properties)

@app.route("/seller/delete/<int:prop_id>", methods=["POST"])
def delete_listing(prop_id):
    if session.get("role") != "Seller": return jsonify({"success": False}), 403
    conn = get_db()
    conn.execute("DELETE FROM properties WHERE id = ? AND owner = ?", (prop_id, session["user"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# --- ADMIN ROUTES ---
@app.route("/admin")
def admin():
    if session.get("role") != "Admin": return redirect("/")
    conn = get_db()
    users_list = conn.execute("SELECT * FROM users").fetchall()
    properties = conn.execute("SELECT * FROM properties").fetchall()
    bookings = conn.execute("SELECT * FROM bookings").fetchall()
    stats = {
        "u_count": len(users_list),
        "p_count": len(properties),
        "b_count": len(bookings)
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


if __name__ == "__main__":
    app.run(debug=True)