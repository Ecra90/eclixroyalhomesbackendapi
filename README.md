# Eclix Royal Homes — Full Stack App

React + Flask + MySQL luxury real estate platform.

---

## Project Structure

```
eclix/
├── backend/
│   ├── app.py            ← Flask API
│   ├── schema.sql        ← MySQL schema + sample data
│   └── requirements.txt
└── frontend/
    ├── public/index.html
    ├── package.json
    └── src/
        ├── App.jsx
        ├── index.js / index.css
        ├── context/AuthContext.jsx
        ├── components/
        │   ├── Navbar.jsx
        │   ├── PropertyCard.jsx
        │   └── Footer.jsx
        └── pages/
            ├── Home.jsx
            ├── Listings.jsx
            ├── Book.jsx      ← requires login
            ├── Auth.jsx      ← Login + Register
            └── Pages.jsx     ← Dashboard, Favourites, About, Contact, Interiors
```

---

## Setup

### 1. Database
```bash
# In phpMyAdmin or mysql CLI:
mysql -u root -p < backend/schema.sql
```

### 2. Backend (Flask)
```bash
cd backend
pip install -r requirements.txt

# Optional: create .env file
# DB_HOST=127.0.0.1
# DB_USER=root
# DB_PASSWORD=your_password
# DB_NAME=eclix_royal_homes
# SECRET_KEY=your_secret_key

python app.py
# Runs on http://localhost:5000
```

### 3. Frontend (React)
```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000
# Proxies /api/* → http://localhost:5000
```

---

## Features

| Feature | Auth Required |
|---------|--------------|
| Browse listings | No |
| Search properties | No |
| Save to favourites | ✅ Yes |
| Book a viewing | ✅ Yes |
| Express purchase interest | ✅ Yes |
| View dashboard & bookings | ✅ Yes |
| Subscribe to newsletter | No |

---

## Auth Flow
- **Session-based** using Flask `session` (cookie)
- Passwords hashed with **bcrypt**
- `login_required` decorator on all protected endpoints
- React `AuthContext` provides `user`, `login()`, `logout()`, `register()`
- Unauthenticated users clicking "Book" or "Favourites" are redirected to `/login`

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | No | Register |
| POST | `/api/auth/login` | No | Login |
| POST | `/api/auth/logout` | No | Logout |
| GET | `/api/auth/me` | No | Current user |
| GET | `/api/properties` | No | List properties (supports `?search=&featured=1`) |
| GET | `/api/properties/:id` | No | Single property |
| GET | `/api/favourites` | ✅ | User's favourites |
| POST | `/api/favourites/:id` | ✅ | Add favourite |
| DELETE | `/api/favourites/:id` | ✅ | Remove favourite |
| GET | `/api/bookings` | ✅ | User's bookings |
| POST | `/api/bookings` | ✅ | Create booking |
| POST | `/api/newsletter` | No | Subscribe |
