# FinLearn AI Deployment Guide

## Architecture
- **Frontend**: Vercel (free)
- **Backend**: AWS EC2 t3.micro (free tier)
- **Database**: Supabase (already configured)

---

## Part 1: Deploy Frontend to Vercel

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Deploy
```bash
cd finlearn-ai-assistant-main
vercel
```

Follow the prompts:
- Set up and deploy? **Y**
- Which scope? Select your account
- Link to existing project? **N**
- Project name? **finlearn-ai**
- Directory? **./** (current)
- Override settings? **N**

### Step 3: Set Environment Variables in Vercel Dashboard
Go to: https://vercel.com/your-username/finlearn-ai/settings/environment-variables

Add:
```
VITE_SUPABASE_URL=https://drmuemzsoeehmxthzpav.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_URL=http://your-ec2-ip:8000
```

### Step 4: Redeploy with env vars
```bash
vercel --prod
```

---

## Part 2: Deploy Backend to AWS EC2

### Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. Settings:
   - **Name**: finlearn-backend
   - **AMI**: Ubuntu 22.04 LTS
   - **Instance type**: t3.micro (free tier)
   - **Key pair**: Create new or use existing
   - **Security Group**: Allow:
     - SSH (port 22) - Your IP
     - HTTP (port 80) - Anywhere
     - HTTPS (port 443) - Anywhere
     - Custom TCP (port 8000) - Anywhere (for API)

3. Launch and note your **Public IP**

### Step 2: Connect to EC2
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### Step 3: Setup Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv git nginx -y

# Clone your repo
git clone https://github.com/YOUR_USERNAME/FinLearnAI.git
cd FinLearnAI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
pip install gunicorn uvicorn[standard]
```

### Step 4: Create Environment File (required for Community + Messages)
```bash
nano backend/.env
```

Add your keys (use the **same** Supabase project as your frontend):
```
GEMINI_API_KEY=your_gemini_key
POLYGON_API_KEY=your_polygon_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
LLM_PROVIDER=gemini
GEMINI_MODEL=models/gemini-flash-latest
```

**Important:** Without `SUPABASE_URL` and `SUPABASE_KEY`, the Community page will only show seed users (no real people to message). Use your Supabase project URL and the **service_role** key (Project Settings → API) so the backend can read `user_profiles` and `direct_messages`. After editing `.env`, run `sudo systemctl restart finlearn`.

### Step 5: Test Backend
```bash
cd backend
python main.py
```

Visit `http://YOUR_EC2_IP:8000/docs` - should see FastAPI docs.

### Step 6: Setup Systemd Service (Auto-restart)
```bash
sudo nano /etc/systemd/system/finlearn.service
```

Paste:
```ini
[Unit]
Description=FinLearn AI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/FinLearnAI/backend
Environment="PATH=/home/ubuntu/FinLearnAI/venv/bin"
ExecStart=/home/ubuntu/FinLearnAI/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable finlearn
sudo systemctl start finlearn
sudo systemctl status finlearn
```

### Step 7: Setup Nginx (Optional - for domain/HTTPS)
```bash
sudo nano /etc/nginx/sites-available/finlearn
```

Paste:
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/finlearn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Part 3: Connect Frontend to Backend

### Update Vercel Environment Variable
In Vercel dashboard, update:
```
VITE_API_URL=http://YOUR_EC2_IP:8000
```

Or if using domain with HTTPS:
```
VITE_API_URL=https://api.yourdomain.com
```

### Redeploy Frontend
```bash
cd finlearn-ai-assistant-main
vercel --prod
```

---

## Useful Commands

### Check backend logs
```bash
sudo journalctl -u finlearn -f
```

### Restart backend
```bash
sudo systemctl restart finlearn
```

### Update code on EC2
```bash
cd ~/FinLearnAI
git pull
sudo systemctl restart finlearn
```

---

## Cost Summary

| Service | Cost |
|---------|------|
| Vercel Frontend | Free |
| EC2 t3.micro | Free (750 hrs/mo for 12 months) |
| Supabase | Free tier |
| **Total** | **$0/month** |

---

## Troubleshooting

### Real users missing on Community / can't message anyone
The backend needs Supabase to show real learners and enable DMs.

1. On EC2, ensure `backend/.env` has **real** values (not placeholders):
   - `SUPABASE_URL=https://your-project.supabase.co`
   - `SUPABASE_KEY=` your **service_role** key from Supabase (Project Settings → API)
2. Make the service load `.env`:
   ```bash
   sudo nano /etc/systemd/system/finlearn.service
   ```
   Under `[Service]`, add this line (after `WorkingDirectory=...`):
   ```ini
   EnvironmentFile=/home/ubuntu/FinLearnAI/backend/.env
   ```
3. Restart and check logs:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart finlearn
   sudo journalctl -u finlearn -n 30
   ```
   You should see `[Supabase] Connected to ...` and `[Users] 12 seed + N real = ...`. If you see "Supabase not configured" or "0 real", fix `.env` and restart again.

### Backend not responding
```bash
sudo systemctl status finlearn
sudo journalctl -u finlearn --no-pager -n 50
```

### CORS errors
Make sure backend CORS allows your Vercel domain.

### Models not loading
t3.micro has 1GB RAM - may need to optimize model loading or use t3.small ($15/mo) if you hit memory issues.
