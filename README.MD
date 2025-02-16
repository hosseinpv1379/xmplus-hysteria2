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

## راه‌اندازی با Crontab

برای اجرای اسکریپت‌ها هر 2 دقیقه یک‌بار، از crontab استفاده می‌کنیم:

1. کرون‌تب را برای کاربر root ویرایش کنید:
```bash
sudo crontab -e
```

2. خط‌های زیر را به کرون‌تب اضافه کنید:
```bash
# همگام‌سازی کاربران هر 2 دقیقه
*/2 * * * * /opt/sui-sync/venv/bin/python /opt/sui-sync/src/main.py

# همگام‌سازی ترافیک هر 2 دقیقه
*/2 * * * * /opt/sui-sync/venv/bin/python /opt/sui-sync/src/sync_usage.py
```

3. برای اطمینان از ثبت کرون‌جاب‌ها:
```bash
sudo crontab -l
```

مطمئن شوید که مسیرها در کرون‌تب با محل نصب اسکریپت‌های شما مطابقت دارد.

## بررسی وضعیت اجرا

برای بررسی لاگ کرون‌جاب‌ها:
```bash
sudo tail -f /var/log/syslog | grep CRON
```

برای بررسی لاگ‌های اسکریپت‌ها:
```bash
tail -f /opt/sui-sync/traffic_sync.log
```

برای بررسی وضعیت کرون‌جاب‌های فعال:
```bash
sudo crontab -l
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
