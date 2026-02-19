from flask import Flask, render_template, request, redirect, session, flash, jsonify
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Database setup remains the same
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, role TEXT)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, location TEXT, price INTEGER, type TEXT, owner TEXT)")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, buyer TEXT, property_title TEXT, status TEXT)")

    cur.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','admin123','Admin')")
    cur.execute("INSERT OR IGNORE INTO users VALUES (2,'seller','seller123','Seller')")
    cur.execute("INSERT OR IGNORE INTO users VALUES (3,'buyer','buyer123','Buyer')")

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
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?",
                            (username, password, role)).fetchone()
        conn.close()

        if user:
            session["user"], session["role"] = username, role
            # Force explicit redirects to match route names exactly
            if role == "Admin": return redirect("/admin")
            if role == "Seller": return redirect("/seller")
            return redirect("/buyer")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username, password, role = request.form["username"], request.form["password"], request.form["role"]
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()
            flash("Registration successful!")
            return redirect("/")
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists.")
        finally:
            conn.close()
    return render_template("signup.html")


@app.route("/buyer")
def buyer():
    if session.get("role") != "Buyer":
        return redirect("/")

    # Get search parameters from the URL
    city_query = request.args.get('city', '')

    conn = get_db()
    if city_query:
        # Search using SQL LIKE for partial matches
        query = "SELECT * FROM properties WHERE location LIKE ?"
        properties = conn.execute(query, ('%' + city_query + '%',)).fetchall()
    else:
        # Default view shows everything
        properties = conn.execute("SELECT * FROM properties").fetchall()

    conn.close()
    return render_template("buyer.html", properties=properties, search_term=city_query)

@app.route("/seller", methods=["GET", "POST"])
def seller():
    if session.get("role") != "Seller": return redirect("/")
    conn = get_db()
    if request.method == "POST":
        title, loc, price, ptype = request.form["title"], request.form["location"], request.form["price"], request.form[
            "type"]
        conn.execute("INSERT INTO properties (title, location, price, type, owner) VALUES (?,?,?,?,?)",
                     (title, loc, price, ptype, session["user"]))
        conn.commit()
    properties = conn.execute("SELECT * FROM properties WHERE owner=?", (session["user"],)).fetchall()
    conn.close()
    return render_template("seller.html", properties=properties)


@app.route("/admin")
def admin():
    if session.get("role") != "Admin":
        return redirect("/")

    conn = get_db()
    users_list = conn.execute("SELECT * FROM users").fetchall()  # Renamed to users_list
    properties = conn.execute("SELECT * FROM properties").fetchall()
    bookings = conn.execute("SELECT * FROM bookings").fetchall()

    # We rename the keys here so they don't clash with the actual data lists
    stats = {
        "u_count": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "p_count": conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0],
        "b_count": conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    }
    conn.close()

    return render_template("admin.html",
                           users=users_list,
                           properties=properties,
                           bookings=bookings,
                           **stats)
@app.route("/book/<int:property_id>", methods=["POST"])
def book(property_id):
    if session.get("role") != "Buyer": return jsonify({"success": False}), 403
    conn = get_db()
    prop = conn.execute("SELECT title FROM properties WHERE id=?", (property_id,)).fetchone()
    if prop:
        conn.execute("INSERT INTO bookings (buyer, property_title, status) VALUES (?, ?, ?)",
                     (session["user"], prop[0], "Pending"))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    conn.close()
    return jsonify({"success": False}), 404


@app.route("/admin/approve/<int:booking_id>")
def approve_booking(booking_id):
    if session.get("role") != "Admin": return jsonify({"error": "Unauthorized"}), 403

    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'Approved' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_status": "Approved"})  # Return JSON


@app.route("/admin/reject/<int:booking_id>")
def reject_booking(booking_id):
    if session.get("role") != "Admin": return jsonify({"error": "Unauthorized"}), 403

    conn = get_db()
    conn.execute("UPDATE bookings SET status = 'Rejected' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_status": "Rejected"})  # Return JSON


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "Admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    conn = get_db()
    # Security check: Prevent admin from deleting themselves
    current_user = conn.execute("SELECT id FROM users WHERE username = ?", (session["user"],)).fetchone()

    if current_user and current_user['id'] == user_id:
        conn.close()
        return jsonify({"success": False, "error": "You cannot delete your own admin account!"}), 400

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)