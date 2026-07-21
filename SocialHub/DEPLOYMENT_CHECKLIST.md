# SocialHub Deployment Checklist

Use this checklist to track your deployment progress on Render.com.

## Pre-Deployment

- [x] Created `render.yaml` configuration file
- [x] Created `Procfile` for Render
- [x] Created `DEPLOYMENT.md` with detailed instructions
- [ ] Code pushed to GitHub/GitLab repository
- [ ] `.env` file backed up (contains email credentials)
- [ ] Strong SECRET_KEY generated (use: `python -c "import secrets; print(secrets.token_urlsafe(48))"`)

## Render Deployment Steps

### 1. Create Render Account
- [ ] Signed up at https://render.com
- [ ] Verified email address
- [ ] Connected GitHub/GitLab account

### 2. Deploy Using Blueprint (Recommended)
- [ ] Go to https://dashboard.render.com/blueprints
- [ ] Click "New Blueprint"
- [ ] Select your SocialHub repository
- [ ] Click "Apply" to deploy all services

**OR** deploy manually:

#### Deploy PostgreSQL Database
- [ ] Created PostgreSQL service named `socialhub-db`
- [ ] Selected Free plan
- [ ] Noted down connection string

#### Deploy Backend API
- [ ] Created Web Service named `socialhub-api`
- [ ] Set build command: `pip install -r requirements.txt`
- [ ] Set start command: `cd backend && python main.py`
- [ ] Added all environment variables (see DEPLOYMENT.md)
- [ ] Added 1GB disk for uploads
- [ ] Noted down backend URL (e.g., https://socialhub-api.onrender.com)

#### Deploy Frontend
- [ ] Created Static Site named `socialhub-frontend`
- [ ] Set publish directory: `./frontend`
- [ ] Added rewrite rules for API routes
- [ ] Noted down frontend URL (e.g., https://socialhub-frontend.onrender.com)

### 3. Post-Deployment Configuration

- [ ] Backend service deployed successfully
- [ ] Frontend service deployed successfully
- [ ] Database is running and connected
- [ ] Ran database migrations: `cd backend && python -m alembic upgrade head`
- [ ] Created admin user via Render shell
- [ ] Tested health endpoint: `/api/health` returns healthy status
- [ ] Tested API docs: `/docs` loads correctly
- [ ] Tested frontend: Homepage loads without errors
- [ ] Tested user registration
- [ ] Tested user login
- [ ] Verified CORS is working (no console errors)

### 4. Security Configuration

- [ ] `DEBUG=false` in production environment
- [ ] Strong `SECRET_KEY` set (32+ characters)
- [ ] `CORS_ORIGINS` updated to actual domain (not `*`)
- [ ] `AUTO_CREATE_TABLES=false` (using migrations)
- [ ] Admin password is strong and secure
- [ ] Email credentials configured (if using email features)
- [ ] Database credentials not exposed in logs

### 5. Optional Configuration

- [ ] Custom domain configured (if applicable)
- [ ] Email verification enabled (if needed)
- [ ] OpenAI API key added (for AI chat features)
- [ ] Instagram OAuth configured (if needed)
- [ ] Redis added for caching (recommended for production)
- [ ] Monitoring alerts configured
- [ ] Auto-deploy enabled from Git repository

## Testing Checklist

### Backend API Tests
- [ ] Health check: `GET https://your-api.onrender.com/api/health`
- [ ] API docs load: `https://your-api.onrender.com/docs`
- [ ] User registration works
- [ ] User login works and returns JWT tokens
- [ ] Protected endpoints require authentication
- [ ] File upload endpoints work
- [ ] WebSocket connection works (for chat)

### Frontend Tests
- [ ] Homepage loads correctly
- [ ] Login/Register pages work
- [ ] Navigation works between pages
- [ ] API calls succeed (check browser console)
- [ ] Images load correctly
- [ ] No CORS errors in console
- [ ] Mobile responsive design works

### Database Tests
- [ ] Users can be created
- [ ] Posts can be created
- [ ] Comments work
- [ ] Likes work
- [ ] Follow system works
- [ ] Stories work
- [ ] Notifications are created

## Production Readiness

- [ ] All tests passing
- [ ] Error monitoring set up (Sentry, etc.)
- [ ] Backup strategy configured
- [ ] Rate limiting enabled
- [ ] SSL certificate active (automatic on Render)
- [ ] Performance tested under load
- [ ] Documentation updated with live URLs
- [ ] Team members have access to Render dashboard

## Your Live URLs

After deployment, update these with your actual Render URLs:

- **Backend API**: `https://socialhub-api.onrender.com`
- **Frontend**: `https://socialhub-frontend.onrender.com`
- **API Docs**: `https://socialhub-api.onrender.com/docs`
- **Health Check**: `https://socialhub-api.onrender.com/api/health`

## Important Notes

⚠️ **Free Tier Limitations:**
- Backend spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- Database expires after 90 days (renewable)
- 1GB disk storage for uploads
- Files are lost when service restarts

💡 **Production Recommendations:**
- Upgrade to paid plan ($7/month) to avoid spin-down
- Use S3/R2 for file storage
- Add Redis for caching
- Set up automated backups
- Monitor performance and errors

## Quick Commands

### Generate SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Run Migrations (in Render shell)
```bash
cd backend
python -m alembic upgrade head
```

### Create Admin User (in Render shell)
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

### Check Logs
```bash
# In Render dashboard: Service → Logs tab
# Or use Render CLI:
render logs -s socialhub-api
```

## Support

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **SocialHub Issues**: Create an issue in your repository

---

**Deployment Date**: _______________

**Deployed By**: _______________

**Live URLs**: _______________

**Notes**: _______________