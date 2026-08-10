# SocialHub Deployment Guide - Render.com

This guide will help you deploy SocialHub on Render.com with a free PostgreSQL database.

## Prerequisites

1. A [Render.com](https://render.com) account (free tier available)
2. Your code pushed to a GitHub/GitLab repository
3. Git installed on your machine

## Step 1: Prepare Your Repository

Ensure these files are in your repository root:
- `render.yaml` (already created)
- `Procfile` (already created)
- `requirements.txt` (already exists)
- `.env` file with your email configuration (DO NOT commit this to git)

## Step 2: Deploy on Render

### Option A: Using render.yaml (Recommended)

1. **Push your code to GitHub/GitLab**
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Create a new Blueprint on Render**
   - Go to https://dashboard.render.com/blueprints
   - Click "New Blueprint"
   - Connect your GitHub/GitLab repository
   - Select your SocialHub repository
   - Render will automatically detect `render.yaml` and deploy all services

3. **Wait for deployment**
   - Render will create:
     - PostgreSQL database (socialhub-db)
     - Backend API service (socialhub-api)
     - Frontend static site (socialhub-frontend)
   - This takes 5-10 minutes on the free tier

### Option B: Manual Deployment

If you prefer manual setup:

#### Deploy PostgreSQL Database

1. Go to https://dashboard.render.com
2. Click "New +" → "PostgreSQL"
3. Fill in:
   - **Name**: `socialhub-db`
   - **Database**: `socialhub`
   - **User**: `socialhub`
   - **Plan**: Free
   - **PostgreSQL Version**: 15
4. Click "Create Database"
5. Note down the **Connection String** (you'll need it)

#### Deploy Backend API

1. Click "New +" → "Web Service"
2. Connect your repository
3. Fill in:
   - **Name**: `socialhub-api`
   - **Runtime**: Python 3
   - **Plan**: Free
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && python main.py`
4. Add Environment Variables:
   ```
   DATABASE_URL=<your-postgres-connection-string>
   DATABASE_URL_ASYNC=<your-postgres-connection-string>
   SECRET_KEY=<generate-a-random-64-char-string>
   DEBUG=false
   AUTO_CREATE_TABLES=false
   CORS_ORIGINS=*
   APP_URL=https://socialhub-api.onrender.com
   EMAIL_VERIFICATION_REQUIRED=false
   AUTO_SCHEMA_COMPATIBILITY=true
   SEED_DEMO_ACCOUNTS=false
   ```
5. Add a disk:
   - **Name**: `uploads`
   - **Mount Path**: `/opt/render/project/src/frontend/uploads`
   - **Size**: 1 GB
6. Click "Create Web Service"

#### Deploy Frontend

1. Click "New +" → "Static Site"
2. Connect your repository
3. Fill in:
   - **Name**: `socialhub-frontend`
   - **Build Command**: `echo "No build needed"`
   - **Publish Directory**: `./frontend`
4. Add Redirect/Rewrite rules:
   ```
   /api/* → https://socialhub-api.onrender.com/api/*
   /uploads/* → https://socialhub-api.onrender.com/uploads/*
   /docs* → https://socialhub-api.onrender.com/docs*
   /redoc* → https://socialhub-api.onrender.com/redoc*
   /ws/* → https://socialhub-api.onrender.com/ws/*
   /* → /index.html
   ```
5. Click "Create Static Site"

## Step 3: Configure Environment Variables

### Required Variables for Backend

Go to your backend service settings → Environment and add:

```env
# Database (auto-configured if using render.yaml)
DATABASE_URL=postgresql://...
DATABASE_URL_ASYNC=postgresql+asyncpg://...

# Security (CRITICAL - Generate a strong random key!)
SECRET_KEY=<use: python -c "import secrets; print(secrets.token_urlsafe(48))">

# Application
DEBUG=false
APP_URL=https://socialhub-api.onrender.com
CORS_ORIGINS=https://socialhub-frontend.onrender.com

# Database Migrations
AUTO_CREATE_TABLES=false
AUTO_SCHEMA_COMPATIBILITY=true

# Features
EMAIL_VERIFICATION_REQUIRED=false
SEED_DEMO_ACCOUNTS=false

# Email (Optional - configure if you want email features)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_USE_STARTTLS=true
```

### Optional Variables

```env
# OpenAI for AI Chat (optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Instagram OAuth (optional)
INSTAGRAM_CLIENT_ID=...
INSTAGRAM_CLIENT_SECRET=...
INSTAGRAM_REDIRECT_URI=https://socialhub-api.onrender.com/api/instagram/callback

# Redis (optional, for production caching)
REDIS_URL=redis://...
```

## Step 4: Run Database Migrations

After the backend deploys:

1. Go to your backend service → "Shell"
2. Run:
   ```bash
   cd backend
   python -m alembic upgrade head
   ```

Or enable auto-migration in the startup event (already configured in main.py).

## Step 5: Create Admin User

1. Go to backend service → "Shell"
2. Run:
   ```bash
   python -c "
   from app.database import SessionLocal
   from app.models.models import User
   from app.utils.security import hash_password
   
   db = SessionLocal()
   admin = User(
       email='admin@socialhub.com',
       username='admin',
       hashed_password=hash_password('YourSecurePassword123!'),
       full_name='Admin User',
       role='admin',
       is_active=True,
       is_banned=False,
       is_email_verified=True
   )
   db.add(admin)
   db.commit()
   print('Admin user created!')
   "
   ```

## Step 6: Test Your Deployment

1. **Backend Health Check**:
   ```
   https://socialhub-api.onrender.com/api/health
   ```
   Should return: `{"success": true, "status": "healthy", "database": "connected"}`

2. **API Documentation**:
   ```
   https://socialhub-api.onrender.com/docs
   ```

3. **Frontend**:
   ```
   https://socialhub-frontend.onrender.com
   ```

## Step 7: Custom Domain (Optional)

1. Go to your frontend/backend service → "Settings"
2. Click "Custom Domain"
3. Add your domain (e.g., `socialhub.com`)
4. Update DNS records as instructed by Render

## Important Notes

### Free Tier Limitations

- **Backend**: Spins down after 15 minutes of inactivity, takes ~30 seconds to wake up
- **Database**: 256 MB storage, expires after 90 days (renewable)
- **Frontend**: 100 GB bandwidth/month
- **No persistent storage**: Uploaded files are lost when service restarts (use S3 for production)

### Production Recommendations

1. **Upgrade to paid plan** ($7/month) to avoid spin-down
2. **Use S3/R2** for file uploads instead of local disk
3. **Add Redis** for caching and rate limiting
4. **Enable email verification** in production
5. **Set up monitoring** (Render provides basic metrics)
6. **Use environment-specific configs** (dev/staging/prod)

### Security Checklist

- [ ] `DEBUG=false` in production
- [ ] Strong `SECRET_KEY` (32+ characters)
- [ ] `CORS_ORIGINS` set to your actual domain (not `*`)
- [ ] `AUTO_CREATE_TABLES=false` (use migrations)
- [ ] Email credentials secured
- [ ] Admin password is strong
- [ ] Database credentials not exposed

## Troubleshooting

### Backend won't start

1. Check logs: Service → "Logs" tab
2. Common issues:
   - Missing environment variables
   - Database connection failed
   - Port already in use (Render sets PORT env var automatically)

### Database connection errors

- Verify DATABASE_URL is set correctly
- Check database is running: Service → "Events"
- Ensure database name/user match

### Frontend shows blank page

- Check browser console for errors
- Verify API routes are rewriting correctly
- Check CORS settings in backend

### Uploads not working

- Verify disk is mounted at `/opt/render/project/src/frontend/uploads`
- Check file permissions
- Remember: Free tier loses files on restart!

## Updating Your Deployment

### Automatic Deployments

Render automatically deploys when you push to your repository:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

### Manual Deployments

Go to your service → "Manual Deploy" → "Deploy latest commit"

## Monitoring

- **Logs**: Service → "Logs" tab (real-time)
- **Metrics**: Service → "Metrics" tab (CPU, memory, response time)
- **Alerts**: Service → "Settings" → "Notifications"

## Support

- Render Docs: https://render.com/docs
- SocialHub Issues: https://github.com/yourusername/socialhub/issues

## Next Steps

1. Set up CI/CD with GitHub Actions
2. Add automated tests
3. Configure backup strategy for database
4. Set up CDN for static assets
5. Add application monitoring (Sentry, etc.)
6. Implement rate limiting
7. Add API versioning