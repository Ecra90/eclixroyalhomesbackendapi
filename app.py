import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
import bcrypt
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)
#stati folder configuration 

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.secret_key = os.environ.get("SECRET_KEY", "eclix-royal-secret-2026")
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    UPLOAD_FOLDER=UPLOAD_FOLDER
)

CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://eclix-royal-homes-and-properties-fi-seven.vercel.app"
    ]
)
@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({
        "success": True,
        "message": "Eclix backend is connected!"
    })

# ─── DB CONFIG ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.environ.get("DB_HOST",),
    "user": os.environ.get("DB_USER",),
    "password": os.environ.get("DB_PASSWORD",),
    "database": os.environ.get("DB_NAME",),
}


def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

# ─── AUTH DECORATOR ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/api/debug/session")
def debug_session():
    return jsonify(dict(session))

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    phone = data.get("phone", "").strip()
    location = data.get("location", "").strip()

    if not all([username, email, password]):
        return jsonify({"error": "Username, email and password are required"}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users_details (username, email, password, phone, location) VALUES (%s, %s, %s, %s, %s)",
            (username, email, hashed, phone, location)
        )
        conn.commit()
        user_id = cursor.lastrowid
        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email
        cursor.close()
        conn.close()
        return jsonify({"message": "Registered successfully", "user": {"id": user_id, "username": username, "email": email}}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users_details WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return jsonify({"error": "Invalid credentials"}), 401

        session["user_id"] = user["userid"]
        session["username"] = user["username"]
        session["email"] = user["email"]
        return jsonify({"message": "Login successful", "user": {
            "id": user["userid"], "username": user["username"], "email": user["email"]
        }})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"user": None})
    return jsonify({"user": {
        "id": session["user_id"],
        "username": session["username"],
        "email": session["email"]
    }})

# ─── PROPERTIES ──────────────────────────────────────────────────────────────
#add properties 

@app.route("/api/properties", methods=["POST"])
@login_required
def add_property():

    property_name = request.form.get("property_name")
    property_location = request.form.get("property_location")
    property_price = request.form.get("property_price")
    property_description = request.form.get("property_description", "")

    property_size = request.form.get("property_size")
    property_bath = request.form.get("property_bath")
    property_beds = request.form.get("property_beds")

    property_featured = request.form.get("property_featured", 0)
    property_for_sale = request.form.get("property_for_sale", 1)

    image = request.files.get("property_photo")

    if not all([property_name, property_location, property_price]):
        return jsonify({"error": "Missing required fields"}), 400

    filename = ""  # ONLY filename stored in DB

    if image:
        os.makedirs("static/uploads", exist_ok=True)

        # ✅ store ONLY original filename (no timestamp, no path)
        filename = image.filename

        save_path = os.path.join("static/uploads", filename)
        image.save(save_path)

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO property_details
            (property_name, property_location, property_price,
             property_description, property_photo,
             property_size, property_featured,
             property_for_sale, property_bath, property_beds)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            property_name,
            property_location,
            property_price,
            property_description,
            filename,   # ✅ ONLY IMAGE NAME SAVED HERE
            property_size,
            property_featured,
            property_for_sale,
            property_bath,
            property_beds
        ))

        conn.commit()
        property_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Property added successfully",
            "property_id": property_id,
            "image": filename
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
      
@app.route("/api/properties", methods=["GET"])
def get_properties():
    search = request.args.get("search", "")
    featured = request.args.get("featured")
    for_sale = request.args.get("for_sale")

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM property_details WHERE 1=1"
        params = []
        if search:
            query += " AND (property_name LIKE %s OR property_location LIKE %s OR property_description LIKE %s)"
            params += [f"%{search}%"] * 3
        if featured:
            query += " AND property_featured = 1"
        if for_sale:
            query += " AND property_for_sale = 1"
        cursor.execute(query, params)
        props = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"properties": props})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/properties/<int:property_id>", methods=["GET"])
def get_property(property_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM property_details WHERE property_id = %s", (property_id,))
        prop = cursor.fetchone()
        cursor.close()
        conn.close()
        if not prop:
            return jsonify({"error": "Property not found"}), 404
        return jsonify({"property": prop})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── FAVOURITES ──────────────────────────────────────────────────────────────
@app.route("/api/favourites", methods=["GET"])
@login_required
def get_favourites():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.* FROM property_details p
            JOIN user_favourites f ON p.property_id = f.property_id
            WHERE f.user_id = %s
        """, (session["user_id"],))
        favs = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"favourites": favs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/favourites/<int:property_id>", methods=["POST", "DELETE"])
@login_required
def toggle_favourite(property_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        if request.method == "POST":
            cursor.execute(
                "INSERT IGNORE INTO user_favourites (user_id, property_id) VALUES (%s, %s)",
                (session["user_id"], property_id)
            )
            msg = "Added to favourites"
        else:
            cursor.execute(
                "DELETE FROM user_favourites WHERE user_id = %s AND property_id = %s",
                (session["user_id"], property_id)
            )
            msg = "Removed from favourites"
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── BOOKINGS ────────────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["POST"])
@login_required
def create_booking():
    data = request.json
    property_id = data.get("property_id")
    booking_type = data.get("booking_type", "viewing")  # viewing | purchase
    notes = data.get("notes", "")
    booking_date = data.get("booking_date")

    if not property_id:
        return jsonify({"error": "Property ID required"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (user_id, property_id, booking_type, notes, booking_date, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW())
        """, (session["user_id"], property_id, booking_type, notes, booking_date))
        conn.commit()
        booking_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"message": "Booking created", "booking_id": booking_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/bookings", methods=["GET"])
@login_required
def get_bookings():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT b.*, p.property_name, p.property_location, p.property_price, p.property_photo
            FROM bookings b
            JOIN property_details p ON b.property_id = p.property_id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
        """, (session["user_id"],))
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        # Convert datetime to string
        for b in bookings:
            if isinstance(b.get("created_at"), datetime):
                b["created_at"] = b["created_at"].isoformat()
            if isinstance(b.get("booking_date"), datetime):
                b["booking_date"] = b["booking_date"].isoformat()
        return jsonify({"bookings": bookings})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── NEWSLETTER ──────────────────────────────────────────────────────────────
@app.route("/api/newsletter", methods=["POST"])
def newsletter():
    email = request.json.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO newsletter_subscribers (email, subscribed_at) VALUES (%s, NOW())", (email,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Subscribed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "message": "Eclix Royal Homes & Properties API is running",
        "api": "/api/properties"
    })
if __name__ == "__main__":
    
    app.run(debug=True, port=5000)
