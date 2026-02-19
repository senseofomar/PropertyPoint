CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, role TEXT);
CREATE TABLE properties (id INTEGER PRIMARY KEY, title TEXT, location TEXT, price REAL, status TEXT, image_url TEXT);
CREATE TABLE bookings (id INTEGER PRIMARY KEY, user_id INTEGER, property_id INTEGER, date TEXT, status TEXT);