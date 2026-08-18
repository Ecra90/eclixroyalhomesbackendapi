import os
from functools import wraps
from datetime import datetime

from flask import Flask, request, jsonify, session
from flask_cors import CORS

import mysql.connector
import bcrypt

import cloudinary
import cloudinary.uploader

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# SECRET KEY / SESSION CONFIGURATION
# ============================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "eclix-royal-secret-2026"
)

app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_NAME="eclix_session"
)


# ============================================================
# CORS
# ============================================================

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://eclix-royal-homes-and-properties-fi-seven.vercel.app"
]

CORS(
    app,
    supports_credentials=True,
    origins=ALLOWED_ORIGINS,
    methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS"
    ],
    allow_headers=[
        "Content-Type",
        "Authorization"
    ]
)


# ============================================================
# CLOUDINARY
# ============================================================

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
}


def get_db():
    """
    Create a new MySQL connection.

    A new connection is created for each request because
    Vercel uses serverless functions.
    """

    required = [
        "DB_HOST",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME"
    ]

    missing = [
        key for key in required
        if not os.environ.get(key)
    ]

    if missing:
        raise RuntimeError(
            "Missing database environment variables: "
            + ", ".join(missing)
        )

    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "online",
        "message": "Eclix Royal Homes & Properties API is running",
        "api": "/api/properties"
    })


@app.route("/api/test", methods=["GET"])
def test():

    return jsonify({
        "success": True,
        "message": "Eclix backend is connected!"
    })


# ============================================================
# AUTH DECORATOR
# ============================================================

def login_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        if "user_id" not in session:

            return jsonify({
                "error": "Authentication required"
            }), 401

        return f(*args, **kwargs)

    return decorated


# ============================================================
# DEBUG SESSION
# ============================================================

@app.route("/api/debug/session", methods=["GET"])
def debug_session():

    return jsonify({
        "session": dict(session)
    })


# ============================================================
# REGISTER
# ============================================================

@app.route("/api/auth/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    username = str(
        data.get("username", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    phone = str(
        data.get("phone", "")
    ).strip()

    location = str(
        data.get("location", "")
    ).strip()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not username:
        return jsonify({
            "error": "Username is required"
        }), 400

    if not email:
        return jsonify({
            "error": "Email is required"
        }), 400

    if not password:
        return jsonify({
            "error": "Password is required"
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters"
        }), 400

    # --------------------------------------------------------
    # HASH PASSWORD
    # --------------------------------------------------------

    try:

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    except Exception as e:

        return jsonify({
            "error": "Password processing failed",
            "details": str(e)
        }), 500

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users_details
            (
                username,
                email,
                password,
                phone,
                location
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                username,
                email,
                hashed_password,
                phone,
                location
            )
        )

        conn.commit()

        user_id = cursor.lastrowid

        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session.clear()

        session["user_id"] = user_id
        session["username"] = username
        session["email"] = email

        return jsonify({
            "message": "Registered successfully",
            "user": {
                "id": user_id,
                "username": username,
                "email": email
            }
        }), 201

    except mysql.connector.IntegrityError as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Email already registered",
            "details": str(e)
        }), 409

    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# LOGIN
# ============================================================

@app.route("/api/auth/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    password = str(
        data.get("password", "")
    )

    if not email or not password:

        return jsonify({
            "error": "Email and password required"
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM users_details
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user:

            return jsonify({
                "error": "Invalid credentials"
            }), 401

        stored_password = user.get("password")

        if not stored_password:

            return jsonify({
                "error": "Account password is invalid"
            }), 401

        try:

            password_valid = bcrypt.checkpw(
                password.encode("utf-8"),
                stored_password.encode("utf-8")
            )

        except Exception:

            password_valid = False

        if not password_valid:

            return jsonify({
                "error": "Invalid credentials"
            }), 401

        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session.clear()

        session["user_id"] = user["userid"]
        session["username"] = user["username"]
        session["email"] = user["email"]

        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user["userid"],
                "username": user["username"],
                "email": user["email"]
            }
        })

    except Exception as e:

        return jsonify({
            "error": "Login failed",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# LOGOUT
# ============================================================

@app.route("/api/auth/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "message": "Logged out successfully"
    })


# ============================================================
# CURRENT USER
# ============================================================

@app.route("/api/auth/me", methods=["GET"])
def me():

    if "user_id" not in session:

        return jsonify({
            "user": None
        })

    return jsonify({
        "user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "email": session.get("email")
        }
    })


# ============================================================
# ADD PROPERTY
# ============================================================

@app.route(
    "/api/properties",
    methods=["POST"]
)
@login_required
def add_property():

    property_name = request.form.get(
        "property_name",
        ""
    ).strip()

    property_location = request.form.get(
        "property_location",
        ""
    ).strip()

    property_price = request.form.get(
        "property_price"
    )

    property_description = request.form.get(
        "property_description",
        ""
    ).strip()

    property_size = request.form.get(
        "property_size"
    )

    property_bath = request.form.get(
        "property_bath"
    )

    property_beds = request.form.get(
        "property_beds"
    )

    property_featured = request.form.get(
        "property_featured",
        "0"
    )

    property_for_sale = request.form.get(
        "property_for_sale",
        "1"
    )

    image = request.files.get(
        "property_photo"
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not property_name:

        return jsonify({
            "error": "Property name is required"
        }), 400

    if not property_location:

        return jsonify({
            "error": "Property location is required"
        }), 400

    if not property_price:

        return jsonify({
            "error": "Property price is required"
        }), 400

    # --------------------------------------------------------
    # CLOUDINARY IMAGE
    # --------------------------------------------------------

    image_url = ""

    if image and image.filename:

        try:

            upload_result = cloudinary.uploader.upload(
                image,
                folder="eclix-properties"
            )

            image_url = upload_result.get(
                "secure_url",
                ""
            )

            if not image_url:

                return jsonify({
                    "error": "Cloudinary did not return an image URL"
                }), 500

        except Exception as e:

            return jsonify({
                "error": "Image upload failed",
                "details": str(e)
            }), 500

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO property_details
            (
                property_name,
                property_location,
                property_price,
                property_description,
                property_photo,
                property_size,
                property_featured,
                property_for_sale,
                property_bath,
                property_beds
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                property_name,
                property_location,
                property_price,
                property_description,
                image_url,
                property_size,
                property_featured,
                property_for_sale,
                property_bath,
                property_beds
            )
        )

        conn.commit()

        property_id = cursor.lastrowid

        return jsonify({
            "message": "Property added successfully",
            "property_id": property_id,
            "image": image_url
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Could not save property",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET ALL PROPERTIES
# ============================================================

@app.route(
    "/api/properties",
    methods=["GET"]
)
def get_properties():

    search = request.args.get(
        "search",
        ""
    ).strip()

    featured = request.args.get(
        "featured"
    )

    for_sale = request.args.get(
        "for_sale"
    )

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        query = """
            SELECT *
            FROM property_details
            WHERE 1=1
        """

        params = []

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        if search:

            query += """
                AND (
                    property_name LIKE %s
                    OR property_location LIKE %s
                    OR property_description LIKE %s
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value,
                search_value
            ])

        # ----------------------------------------------------
        # FEATURED
        # ----------------------------------------------------

        if featured == "1":

            query += """
                AND property_featured = 1
            """

        # ----------------------------------------------------
        # FOR SALE
        # ----------------------------------------------------

        if for_sale == "1":

            query += """
                AND property_for_sale = 1
            """

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

        query += """
            ORDER BY property_id DESC
        """

        cursor.execute(
            query,
            params
        )

        properties = cursor.fetchall()

        return jsonify({
            "properties": properties
        })

    except Exception as e:

        return jsonify({
            "error": "Could not load properties",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET SINGLE PROPERTY
# ============================================================

@app.route(
    "/api/properties/<int:property_id>",
    methods=["GET"]
)
def get_property(property_id):

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM property_details
            WHERE property_id = %s
            LIMIT 1
            """,
            (property_id,)
        )

        property_data = cursor.fetchone()

        if not property_data:

            return jsonify({
                "error": "Property not found"
            }), 404

        return jsonify({
            "property": property_data
        })

    except Exception as e:

        return jsonify({
            "error": "Could not load property",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET FAVOURITES
# ============================================================

@app.route(
    "/api/favourites",
    methods=["GET"]
)
@login_required
def get_favourites():

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT p.*
            FROM property_details p
            INNER JOIN user_favourites f
                ON p.property_id = f.property_id
            WHERE f.user_id = %s
            ORDER BY p.property_id DESC
            """,
            (session["user_id"],)
        )

        favourites = cursor.fetchall()

        return jsonify({
            "favourites": favourites
        })

    except Exception as e:

        return jsonify({
            "error": "Could not load favourites",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# ADD / REMOVE FAVOURITE
# ============================================================

@app.route(
    "/api/favourites/<int:property_id>",
    methods=["POST", "DELETE"]
)
@login_required
def toggle_favourite(property_id):

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor()

        # ----------------------------------------------------
        # ADD
        # ----------------------------------------------------

        if request.method == "POST":

            cursor.execute(
                """
                INSERT IGNORE INTO user_favourites
                (
                    user_id,
                    property_id
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    property_id
                )
            )

            message = "Added to favourites"

        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        else:

            cursor.execute(
                """
                DELETE FROM user_favourites
                WHERE user_id = %s
                AND property_id = %s
                """,
                (
                    session["user_id"],
                    property_id
                )
            )

            message = "Removed from favourites"

        conn.commit()

        return jsonify({
            "message": message
        })

    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Favourite operation failed",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# CREATE BOOKING
# ============================================================

@app.route(
    "/api/bookings",
    methods=["POST"]
)
@login_required
def create_booking():

    data = request.get_json(
        silent=True
    ) or {}

    property_id = data.get(
        "property_id"
    )

    booking_type = data.get(
        "booking_type",
        "viewing"
    )

    notes = data.get(
        "notes",
        ""
    )

    booking_date = data.get(
        "booking_date"
    )

    if not property_id:

        return jsonify({
            "error": "Property ID required"
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor()

        # ----------------------------------------------------
        # CHECK PROPERTY EXISTS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT property_id
            FROM property_details
            WHERE property_id = %s
            LIMIT 1
            """,
            (property_id,)
        )

        property_exists = cursor.fetchone()

        if not property_exists:

            return jsonify({
                "error": "Property not found"
            }), 404

        # ----------------------------------------------------
        # CREATE BOOKING
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO bookings
            (
                user_id,
                property_id,
                booking_type,
                notes,
                booking_date,
                status,
                created_at
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'pending',
                NOW()
            )
            """,
            (
                session["user_id"],
                property_id,
                booking_type,
                notes,
                booking_date
            )
        )

        conn.commit()

        booking_id = cursor.lastrowid

        return jsonify({
            "message": "Booking created successfully",
            "booking_id": booking_id
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Could not create booking",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET BOOKINGS
# ============================================================

@app.route(
    "/api/bookings",
    methods=["GET"]
)
@login_required
def get_bookings():

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                b.*,
                p.property_name,
                p.property_location,
                p.property_price,
                p.property_photo
            FROM bookings b
            INNER JOIN property_details p
                ON b.property_id = p.property_id
            WHERE b.user_id = %s
            ORDER BY b.created_at DESC
            """,
            (session["user_id"],)
        )

        bookings = cursor.fetchall()

        # ----------------------------------------------------
        # CONVERT DATETIME VALUES TO JSON SAFE STRINGS
        # ----------------------------------------------------

        for booking in bookings:

            if isinstance(
                booking.get("created_at"),
                (datetime,)
            ):

                booking["created_at"] = (
                    booking["created_at"].isoformat()
                )

            if isinstance(
                booking.get("booking_date"),
                (datetime,)
            ):

                booking["booking_date"] = (
                    booking["booking_date"].isoformat()
                )

        return jsonify({
            "bookings": bookings
        })

    except Exception as e:

        return jsonify({
            "error": "Could not load bookings",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# NEWSLETTER
# ============================================================

@app.route(
    "/api/newsletter",
    methods=["POST"]
)
def newsletter():

    data = request.get_json(
        silent=True
    ) or {}

    email = str(
        data.get("email", "")
    ).strip().lower()

    if not email:

        return jsonify({
            "error": "Email required"
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT IGNORE INTO newsletter_subscribers
            (
                email,
                subscribed_at
            )
            VALUES
            (
                %s,
                NOW()
            )
            """,
            (email,)
        )

        conn.commit()

        return jsonify({
            "message": "Subscribed successfully"
        }), 201

    except Exception as e:

        if conn:
            conn.rollback()

        return jsonify({
            "error": "Newsletter subscription failed",
            "details": str(e)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error": "Endpoint not found",
        "path": request.path
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "error": "Method not allowed",
        "method": request.method,
        "path": request.path
    }), 405


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "error": "Internal server error"
    }), 500


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )