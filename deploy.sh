#!/bin/bash
set -e

DOMAIN="srv1414244.hstgr.cloud"
EMAIL_SSL="leonardozacharias@gmail.com"
APP_DIR="/opt/shipyard"
APP_USER="shipyard"

echo "════════════════════════════════════════════"
echo "  ⛵ SHIPYARD — Deploy VPS Hostinger"
echo "════════════════════════════════════════════"

echo "📦 [1/6] Atualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq python3 python3-pip python3-venv python3-dev \
    nginx certbot python3-certbot-nginx git curl build-essential \
    libssl-dev libffi-dev

echo "👤 [2/6] Criando usuário $APP_USER..."
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER
chown -R $APP_USER:$APP_USER $APP_DIR

echo "🐍 [3/6] Configurando ambiente Python..."
sudo -u $APP_USER python3 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -q \
    streamlit streamlit-authenticator \
    pandas numpy scipy yfinance \
    plotly requests \
    python-dotenv apscheduler \
    bcrypt pyyaml openpyxl pyarrow

echo "⚙️  [4/6] Configurando .env e auth..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp $APP_DIR/.env.example $APP_DIR/.env
fi
mkdir -p $APP_DIR/logs
chown -R $APP_USER:$APP_USER $APP_DIR

echo "🔧 [5/6] Configurando serviços systemd..."
cat > /etc/systemd/system/shipyard-dashboard.service << SVCEOF
[Unit]
Description=Shipyard Vela Capital — Dashboard
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/streamlit run dashboard.py \
    --server.port=8501 \
    --server.address=127.0.0.1 \
    --server.headless=true \
    --browser.gatherUsageStats=false
Restart=on-failure
RestartSec=10
StandardOutput=append:$APP_DIR/logs/dashboard.log
StandardError=append:$APP_DIR/logs/dashboard.log

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/shipyard-scheduler.service << SVCEOF
[Unit]
Description=Shipyard Vela Capital — Scheduler
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/python scheduler.py
Restart=on-failure
RestartSec=30
StandardOutput=append:$APP_DIR/logs/scheduler.log
StandardError=append:$APP_DIR/logs/scheduler.log

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable shipyard-dashboard shipyard-scheduler

echo "🌐 [6/6] Configurando Nginx..."
cat > /etc/nginx/sites-available/shipyard << NGXEOF
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass         http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host \$host;
        proxy_read_timeout 86400;
        proxy_buffering    off;
    }
    location /_stcore/stream {
        proxy_pass         http://127.0.0.1:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
NGXEOF

ln -sf /etc/nginx/sites-available/shipyard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo "🔐 Gerando credenciais dashboard..."
sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/setup_auth.py

echo "🚀 Rodando valuation inicial..."
sudo -u $APP_USER $APP_DIR/venv/bin/python $APP_DIR/main.py

echo "▶  Iniciando serviços..."
systemctl start shipyard-dashboard shipyard-scheduler

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ DEPLOY CONCLUÍDO!"
echo "  🌐 http://$DOMAIN"
echo "════════════════════════════════════════════"
