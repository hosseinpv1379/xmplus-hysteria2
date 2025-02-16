# XMPlus Hysteria2 Sync

این پروژه یک سیستم همگام‌سازی بین XMPlus و S-UI است که امکان مدیریت خودکار کاربران و ترافیک را فراهم می‌کند.

## پیش‌نیازها

- Python 3.8 یا بالاتر
- S-UI نصب شده
- دسترسی به دیتابیس XMPlus
- سیستم عامل لینوکس (ترجیحاً Ubuntu/Debian)

## نصب

1. ابتدا مخزن را کلون کنید:
```bash
git clone https://github.com/hosseinpv1379/xmplus-hysteria2.git
cd xmplus-hysteria2
```

2. محیط مجازی Python را ایجاد و فعال کنید:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. وابستگی‌های پروژه را نصب کنید:
```bash
pip install -r requirements.txt
```

4. دایرکتوری پروژه را به مسیر مناسب منتقل کنید:
```bash
sudo mkdir -p /opt/sui-sync
sudo cp -r * /opt/sui-sync/
```

## پیکربندی

1. فایل پیکربندی را ویرایش کنید:
```bash
sudo nano /opt/sui-sync/config.json
```

2. اطلاعات زیر را در فایل `config.json` وارد کنید:
```json
{
    "database": {
        "sui_db_path": "/usr/local/s-ui/db/s-ui.db",
        "xmplus": {
            "host": "آدرس_دیتابیس_XMPlus",
            "user": "نام_کاربری_دیتابیس",
            "password": "رمز_عبور_دیتابیس",
            "database": "نام_دیتابیس_XMPlus"
        }
    },
    "sync": {
        "interval": 300,
        "restart_sui": true
    }
}
```

## راه‌اندازی سرویس‌ها

1. برای همگام‌سازی کاربران، سرویس زیر را ایجاد کنید:
```bash
sudo nano /etc/systemd/system/sui-sync.service
```

محتوای فایل سرویس:
```ini
[Unit]
Description=S-UI User Sync Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sui-sync
Environment=PYTHONPATH=/opt/sui-sync
ExecStart=/opt/sui-sync/venv/bin/python /opt/sui-sync/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. برای همگام‌سازی ترافیک، سرویس دیگری ایجاد کنید:
```bash
sudo nano /etc/systemd/system/sui-sync-usage.service
```

محتوای فایل سرویس:
```ini
[Unit]
Description=S-UI Traffic Sync Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sui-sync
Environment=PYTHONPATH=/opt/sui-sync
ExecStart=/opt/sui-sync/venv/bin/python /opt/sui-sync/sync_usage.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. سرویس‌ها را فعال و اجرا کنید:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sui-sync
sudo systemctl enable sui-sync-usage
sudo systemctl start sui-sync
sudo systemctl start sui-sync-usage
```

## بررسی وضعیت سرویس‌ها

برای بررسی وضعیت سرویس‌ها:
```bash
sudo systemctl status sui-sync
sudo systemctl status sui-sync-usage
```

برای مشاهده لاگ‌ها:
```bash
sudo journalctl -u sui-sync -f
sudo journalctl -u sui-sync-usage -f
```

## عملکرد

- `main.py`: این اسکریپت کاربران فعال را از XMPlus دریافت کرده و آنها را در S-UI همگام‌سازی می‌کند.
- `sync_usage.py`: این اسکریپت ترافیک مصرفی کاربران را از S-UI به XMPlus منتقل می‌کند.

## نکات مهم

1. اطمینان حاصل کنید که مسیر دیتابیس S-UI در `config.json` صحیح است.
2. دسترسی‌های لازم برای دیتابیس XMPlus را در `config.json` به درستی تنظیم کنید.
3. سرویس‌ها به صورت خودکار پس از راه‌اندازی سیستم اجرا می‌شوند.
4. در صورت تغییر در کد، سرویس‌ها را مجدداً راه‌اندازی کنید.

## عیب‌یابی

اگر سرویس‌ها به درستی کار نمی‌کنند:

1. لاگ‌ها را بررسی کنید:
```bash
tail -f /opt/sui-sync/traffic_sync.log
```

2. دسترسی‌های فایل‌ها را چک کنید:
```bash
sudo chown -R root:root /opt/sui-sync
sudo chmod -R 755 /opt/sui-sync
```

3. اتصال به دیتابیس‌ها را بررسی کنید:
```bash
# بررسی دسترسی به دیتابیس S-UI
ls -l /usr/local/s-ui/db/s-ui.db

# تست اتصال به دیتابیس XMPlus
mysql -h HOST -u USER -p DATABASE
```

## مشارکت

پول ریکوئست‌ها و گزارش مشکلات از طریق GitHub پذیرفته می‌شود.

## لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.
