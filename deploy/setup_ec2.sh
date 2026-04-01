#!/bin/bash
# FinLearn AI - EC2 Setup Script
# Run this after SSH-ing into your EC2 instance

set -e

echo "=========================================="
echo "FinLearn AI Backend Setup"
echo "=========================================="

# Update system
echo "[1/7] Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "[2/7] Installing Python and dependencies..."
sudo apt install python3-pip python3-venv git nginx -y

# Clone repo (update with your GitHub URL)
echo "[3/7] Cloning repository..."
if [ ! -d "FinLearnAI" ]; then
    git clone https://github.com/YOUR_USERNAME/FinLearnAI.git
fi
cd FinLearnAI

# Create virtual environment
echo "[4/7] Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[5/7] Installing Python packages..."
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install gunicorn uvicorn[standard]

# Create .env file template
echo "[6/7] Creating .env template..."
if [ ! -f "backend/.env" ]; then
    cat > backend/.env << 'EOF'
# FinLearn AI Backend Environment Variables
# Fill in your actual keys!

GEMINI_API_KEY=your_gemini_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
SUPABASE_URL=https://drmuemzsoeehmxthzpav.supabase.co
SUPABASE_KEY=your_supabase_service_key_here
LLM_PROVIDER=gemini
GEMINI_MODEL=models/gemini-flash-latest
EOF
    echo "⚠️  IMPORTANT: Edit backend/.env with your actual API keys!"
    echo "   Run: nano backend/.env"
fi

# Create systemd service (loads backend/.env so Supabase + API keys work for Community/Messages)
echo "[7/7] Creating systemd service..."
sudo tee /etc/systemd/system/finlearn.service > /dev/null << EOF
[Unit]
Description=FinLearn AI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/FinLearnAI/backend
EnvironmentFile=/home/ubuntu/FinLearnAI/backend/.env
Environment="PATH=/home/ubuntu/FinLearnAI/venv/bin"
ExecStart=/home/ubuntu/FinLearnAI/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable finlearn

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit your API keys: nano backend/.env"
echo "2. Start the service: sudo systemctl start finlearn"
echo "3. Check status: sudo systemctl status finlearn"
echo "4. View logs: sudo journalctl -u finlearn -f"
echo ""
echo "Your API will be at: http://$(curl -s ifconfig.me):8000"
echo ""
