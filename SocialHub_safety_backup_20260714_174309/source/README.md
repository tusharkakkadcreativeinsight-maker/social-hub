# SocialHub - Social Media Platform

A complete, production-ready social media platform built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **JWT Authentication**, **WebSockets**, and **Bootstrap Frontend**.

## Features

### Authentication
- User Registration with email verification
- Login/Logout with JWT Access & Refresh Tokens
- Forgot Password & Reset Password via email
- Role-Based Access Control (Admin/User)
- Email verification system

### User Profile
- Profile picture & cover photo upload
- Bio, username, website, location
- Edit profile information
- Public/Private account settings

### Posts
- Create, edit, delete posts with rich text
- Multiple image upload support
- Video upload support
- Hashtag support
- Tag users in posts
- Post feed from followed users

### Likes & Comments
- Like/unlike posts with reaction system (like, love, haha, wow, sad, angry)
- Comment on posts
- Reply to comments (nested comments)
- Delete comments

### Follow System
- Follow/unfollow users
- Followers & following lists
- Follow requests for private accounts
- Accept/reject follow requests

### Stories
- Upload image/video stories
- Auto-delete after 24 hours
- Story reactions
- View stories slideshow

### Reels
- Upload short-form videos
- Like, comment, and share reels
- View counter

### Messaging (Real-Time)
- Real-time chat using WebSockets
- Private 1-on-1 messaging
- Group chat support
- Typing indicators
- Read receipts
- Image/file sharing in chat

### Notifications
- Follow notifications
- Like notifications
- Comment notifications
- Follow request notifications
- Accept follow notifications
- Tag notifications

### Search
- Search users by username/name/email
- Search posts by content
- Search hashtags with post count

### Admin Panel
- Dashboard with statistics
- User management (ban/unban)
- Post management
- Reports management
- Analytics data

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | FastAPI |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Authentication** | JWT (python-jose) |
| **Password Hashing** | bcrypt (passlib) |
| **Validation** | Pydantic v2 |
| **WebSockets** | FastAPI WebSocket |
| **Frontend** | HTML5, CSS3, Vanilla JS |
| **Icons** | Font Awesome 6 |
| **Email** | SMTP (Gmail) |

## Project Structure

```
SocialHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py          # Application configuration
│   │   ├── database.py         # Database connection & session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── models.py      # All SQLAlchemy models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── users.py       # User profile endpoints
│   │   │   ├── posts.py       # Post CRUD endpoints
│   │   │   ├── likes.py       # Like endpoints
│   │   │   ├── comments.py    # Comment endpoints
│   │   │   ├── followers.py   # Follow system endpoints
│   │   │   ├── stories.py     # Story endpoints
│   │   │   ├── reels.py       # Reel endpoints
│   │   │   ├── messaging.py   # Chat/message endpoints
│   │   │   ├── notifications.py # Notification endpoints
│   │   │   ├── search.py      # Search endpoints
│   │   │   ├── reports.py     # Report endpoints
│   │   │   └── admin.py       # Admin panel endpoints
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   └── chat.py        # WebSocket chat handler
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── security.py    # JWT & password utilities
│   │       ├── dependencies.py # FastAPI dependencies
│   │       └── email.py       # Email sending utilities
│   ├── alembic/
│   │   ├── env.py             # Alembic environment
│   │   └── versions/          # Migration files
│   ├── alembic.ini            # Alembic configuration
│   └── main.py                # Application entry point
├── frontend/
│   ├── templates/             # HTML templates
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── profile.html
│   │   ├── posts.html
│   │   ├── chat.html
│   │   ├── stories.html
│   │   ├── reels.html
│   │   ├── notifications.html
│   │   ├── search.html
│   │   ├── admin.html
│   │   ├── forgot_password.html
│   │   └── reset_password.html
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css      # Complete stylesheet
│   │   └── js/
│   │       └── app.js         # Frontend JavaScript
│   └── uploads/               # User uploaded files
│       ├── profile_pics/
│       ├── cover_photos/
│       ├── post_images/
│       ├── videos/
│       ├── reels/
│       └── stories/
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables example
└── README.md                  # This file
```

## Database Tables

| Table | Description |
|-------|-------------|
| `users` | User accounts |
| `profiles` | User profile information |
| `posts` | User posts |
| `post_images` | Post media (images/videos) |
| `likes` | Post likes with reactions |
| `comments` | Post comments with replies |
| `followers` | Follow relationships |
| `stories` | User stories (24h expiry) |
| `story_reactions` | Story reactions |
| `reels` | Short-form videos |
| `reel_likes` | Reel likes |
| `reel_comments` | Reel comments |
| `chats` | Chat conversations |
| `messages` | Chat messages |
| `notifications` | User notifications |
| `reports` | User/post reports |
| `roles` | Role definitions |

## Quick Start (local development)

From the project root:

```powershell
cd SocialHub
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

Open: http://127.0.0.1:8000

SQLite is the default local fallback. To use PostgreSQL, copy `.env.example` to `.env` and set `DATABASE_URL` / `DATABASE_URL_ASYNC`.

## Required checks

Run these before committing changes:

```powershell
cd SocialHub
python -m pytest -q
python -m py_compile backend/**/*.py
node --check frontend/static/js/app.js
```

If your Windows shell does not expand `backend/**/*.py`, use this equivalent compile check:

```powershell
python -m compileall -q backend
```

## Media upload path rules

Uploaded media is stored in `frontend/uploads/`, and database values must stay clean relative paths only:

- Posts: `posts/file.png` or `posts/file.mp4`
- Reels: `reels/file.mp4`
- Stories: `stories/file.png` or `stories/file.mp4`
- Profile pictures: `profiles/file.png`
- Covers: `covers/file.png`

Frontend media is loaded through `/uploads/<relative_path>`.

## Windows PostgreSQL Quick Start

1. Install PostgreSQL for Windows.
2. Open pgAdmin or psql.
3. Create the production database:

`sql
CREATE DATABASE socialhub;
`

4. Create SocialHub/.env from .env.example and set:

`env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/socialhub
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/socialhub
SECRET_KEY=change-to-long-secret-key
DEBUG=true
CORS_ORIGINS=*
`

5. Install dependencies from the project root:

`powershell
cd SocialHub
pip install -r requirements.txt
`

6. Run checks and start:

`powershell
cd backend
python test_db.py
python main.py
`

7. Open http://127.0.0.1:8000

Production note: keep DEBUG=false and run Alembic migrations with lembic upgrade head instead of relying on auto-create tables. SQLite remains only a local fallback when PostgreSQL is unavailable.

## Installation Guide

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/socialhub.git
cd socialhub
```

### Step 2: Setup PostgreSQL Database

```sql
CREATE DATABASE socialhub;
CREATE USER socialhub_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE socialhub TO socialhub_user;
```

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DATABASE_URL=postgresql://socialhub_user:your_password@localhost:5432/socialhub
SECRET_KEY=your-strong-secret-key-here
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Step 4: Install Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

### Step 5: Run Database Migrations

```bash
alembic upgrade head
```

Or let FastAPI auto-create tables on startup.

### Step 6: Run the Application

```bash
python main.py
```

The server will start at `http://localhost:8000`

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/verify-email` | Verify email address |
| POST | `/api/auth/forgot-password` | Send reset password email |
| POST | `/api/auth/reset-password` | Reset password |
| GET | `/api/auth/me` | Get current user info |
| GET | `/api/users/profile/{username}` | Get user profile |
| PUT | `/api/users/profile` | Update profile |
| POST | `/api/users/profile/picture` | Upload profile picture |
| POST | `/api/users/profile/cover` | Upload cover photo |
| GET/POST | `/api/posts` | List/Create posts |
| GET/PUT/DELETE | `/api/posts/{id}` | Get/Update/Delete post |
| POST/DELETE | `/api/likes/{post_id}` | Like/Unlike post |
| GET/POST | `/api/comments/{post_id}` | List/Create comments |
| PUT/DELETE | `/api/comments/{comment_id}` | Update/Delete comment |
| POST/DELETE | `/api/follow/{user_id}` | Follow/Unfollow user |
| GET | `/api/follow/followers/{user_id}` | Get followers |
| GET | `/api/follow/following/{user_id}` | Get following |
| POST | `/api/stories` | Create story |
| GET | `/api/stories` | Get stories feed |
| POST | `/api/reels` | Create reel |
| GET | `/api/reels` | Get reels feed |
| POST | `/api/chats` | Create chat |
| GET | `/api/chats` | Get user chats |
| GET/POST | `/api/chats/{id}/messages` | List/Send messages |
| GET | `/api/notifications` | Get notifications |
| GET | `/api/search` | Global search |
| POST | `/api/reports` | Create report |
| GET | `/api/admin/dashboard` | Admin dashboard |
| GET | `/api/admin/users` | Admin user management |
| PUT | `/api/admin/users/{id}/ban` | Ban/Unban user |

## WebSocket Chat

Connect to the WebSocket endpoint:

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/chat?token=${TOKEN}`);
```

### WebSocket Message Types

**Client → Server:**
- `join` - Join a chat room
- `leave` - Leave a chat room
- `message` - Send a message
- `typing` - Typing indicator
- `read` - Mark messages as read

**Server → Client:**
- `new_message` - New message received
- `typing` - User typing status
- `user_online` - User came online
- `user_offline` - User went offline
- `messages_read` - Messages read by recipient

## Creating Admin User

Run this SQL to create an admin user:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

Or register normally and update the role in the database.

## License

MIT License

## Support

For support, email support@socialhub.com or create an issue on GitHub.