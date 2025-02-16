و حالا اسکریپت نصب تعاملی `install.sh`:

```bash
#!/bin/bash

# تنظیم رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# بررسی دسترسی root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}لطفاً با دسترسی root اجرا کنید${NC}"
    exit 1
fi

# تابع برای گرفتن ورودی و ذخیره در config.json
configure_service() {
    echo -e "${BLUE}شروع پیکربندی سرویس...${NC}"
    
    # ایجاد فایل کانفیگ موقت
    temp_config=$(mktemp)
    
    # دریافت اطلاعات دیتابیس
    read -p "آدرس دیتابیس XMPlus را وارد کنید: " db_host
    read -p "نام کاربری دیتابیس: " db_user
    read -p "رمز عبور دیتابیس: " db_pass
    read -p "نام دیتابیس: " db_name
    
    # دریافت اطلاعات سرور
    read -p "آدرس IP سرور اصلی: " server_ip
    read -p "پورت Hysteria2 (پیش‌فرض: 443): " server_port
    server_port=${server_port:-443}
    
    # ساخت فایل config.json
    cat > "$temp_config" << EOF
{
  "database": {
    "sui_db_path": "/usr/local/s-ui/db/s-ui.db",
    "xmplus": {
      "host": "$db_host",
      "user": "$db_user",
      "password": "$db_pass",
      "database": "$db_name"
    }
  },
  "sync": {
    "interval": 300,
    "restart_sui": true
  },
  "subscription": {
    "servers": [
      {
        "name": "Server 1",
        "ip": "$server_ip",
        "port": $server_port,
        "obfs": "salamander",
        "obfs_password": "2bxq67sohw9k1av83vk8f7h2it6v95b63xyitu2f0n50yxbq"
      }
    ],
    "subscription_names": {
      "client1": "Service Provider 1"
    },
    "api": {
      "base_url": "https://bugde1-alphatm.best",
      "endpoint": "/link"
    },
    "port": 5000
  }
}
EOF

    # انتقال فایل کانفیگ به مسیر نهایی
    mkdir -p /opt/sui-sync
    mv "$temp_config" /opt/sui-sync/config.json
    
    echo -e "${GREEN}فایل کانفیگ ایجاد شد${NC}"
}

# نصب پکیج‌های مورد نیاز
install_requirements() {
    echo -e "${BLUE}نصب پکیج‌های مورد نیاز...${NC}"
    
    apt-get update
    apt-get install -y python3 python3-pip nginx certbot python3-certbot-nginx
    
    pip3 install -r requirements.txt
}

# پیکربندی Nginx
configure_nginx() {
    echo -e "${BLUE}پیکربندی Nginx...${NC}"
    
    read -p "دامنه خود را وارد کنید: " domain
    
    # ایجاد کانفیگ Nginx
    cat > /etc/nginx/sites-available/subscription << EOF
server {
    listen 80;
    server_name $domain;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $domain;

    ssl_certificate /etc/letsencrypt/live/$domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$domain/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/subscription /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # نصب SSL
    certbot --nginx -d "$domain" --non-interactive --agree-tos --email admin@"$domain"
    
    systemctl restart nginx
}

# نصب سرویس‌ها
install_services() {
    echo -e "${BLUE}نصب سرویس‌ها...${NC}"
    
    # کپی فایل‌ها
    cp -r src/* /opt/sui-sync/
    
    # ایجاد سرویس‌های systemd
    for service in sync-users sync-usage subscription; do
        cat > "/etc/systemd/system/$service.service" << EOF
[Unit]
Description=$service Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/sui-sync/${service}.py
Restart=always
User=root
WorkingDirectory=/opt/sui-sync

[Install]
WantedBy=multi-user.target
EOF
    done
    
    # فعال‌سازی و شروع سرویس‌ها
    systemctl daemon-reload
    for service in sync-users sync-usage subscription; do
        systemctl enable "$service"
        systemctl start "$service"
    done
}

# اجرای اصلی
echo -e "${GREEN}شروع نصب سرویس...${NC}"

configure_service
install_requirements
configure_nginx
install_services

echo -e "${GREEN}نصب با موفقیت انجام شد!${NC}"
echo -e "برای بررسی وضعیت سرویس‌ها:"
echo -e "systemctl status sync-users sync-usage subscription"
