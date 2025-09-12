# Render Deployment Guide

## 🚀 Deploy to Render

### 1. Environment Variables

Set these in your Render dashboard:

**Required:**
- `POLAROO_EMAIL` - Your Polaroo email
- `POLAROO_PASSWORD` - Your Polaroo password  
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_KEY` - Your Supabase service key
- `COHERE_API_KEY` - Your Cohere API key

**Optional (defaults provided):**
- `STORAGE_BUCKET` - polaroo_pdfs (already set)
- `STORAGE_PREFIX` - raw (default)

### 2. Deployment Steps

1. **Connect your GitHub repo** to Render
2. **Create a new Web Service**
3. **Use these settings:**
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     playwright install chromium
     playwright install-deps chromium
     apt-get update && apt-get install -y google-chrome-stable
     ```
   - **Start Command:**
     ```bash
     uvicorn src.api_supabase:app --host 0.0.0.0 --port $PORT
     ```
   - **Environment:** Python 3
   - **Region:** Choose closest to your users

### 3. Health Check

After deployment, test these endpoints:

- **Basic health:** `https://your-app.onrender.com/api/health`
- **Detailed health:** `https://your-app.onrender.com/api/health/detailed`
- **Properties:** `https://your-app.onrender.com/api/properties`

### 4. API Endpoints

**New Supabase API endpoints:**
- `POST /api/process-property` - Process single property
- `POST /api/process-batch` - Process multiple properties
- `GET /api/sessions` - Get processing sessions
- `GET /api/export/session/{id}/csv` - Export results as CSV
- `GET /api/export/session/{id}/excel` - Export results as Excel

**Legacy compatibility:**
- `POST /api/calculate` - Legacy calculation endpoint
- `GET /api/configuration` - Get system configuration

### 5. Troubleshooting

**Common issues:**
- **Build fails:** Check Python version (3.8+)
- **Playwright issues:** Ensure chromium is installed
- **Database errors:** Verify Supabase credentials
- **File upload fails:** Check storage bucket exists

**Logs:**
- Check Render logs for detailed error messages
- Test locally first: `python -m src.api_supabase`

### 6. Performance

**Optimizations:**
- **Memory:** Render free tier has 512MB limit
- **CPU:** Free tier has 0.1 CPU
- **Storage:** 1GB limit on free tier
- **Timeout:** 15 minutes max on free tier

**For production:**
- Upgrade to paid plan for better performance
- Consider using Render's database add-ons
- Monitor usage and scale as needed

### 7. Monitoring

**Health checks:**
- Use `/api/health` for basic monitoring
- Use `/api/health/detailed` for system status
- Monitor Render dashboard for resource usage

**Alerts:**
- Set up alerts for failed deployments
- Monitor response times
- Track error rates

## 🎯 Ready to Deploy!

Your app is now ready for Render deployment with full Supabase integration!
