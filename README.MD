ابتدا `README.md` فارسی برای آموزش:

```markdown
# نصب و راه‌اندازی سرویس VPN

## پیش‌نیازها
- اوبونتو 20.04 یا بالاتر
- دسترسی root
- دامنه که به سرور شما متصل است

## مراحل نصب

1. دانلود کنید:
```bash
git clone https://github.com/yourusername/vpn-service.git
cd vpn-service
```

2. فایل `config.json` را ویرایش کنید:
   - تنظیمات دیتابیس
   - آدرس IP سرورها
   - نام‌های سرویس‌ها
   - تنظیمات API

3. اجرای اسکریپت نصب:
```bash
sudo bash install.sh
```

4. اطلاعات درخواستی را وارد کنید:
   - دامنه
   - پورت‌ها
   - نام‌های سرویس

## بررسی وضعیت سرویس‌ها
```bash
sudo systemctl status sync-users
sudo systemctl status sync-usage
sudo systemctl status subscription
```

## مشاهده لاگ‌ها
```bash
sudo journalctl -u sync-users
sudo journalctl -u sync-usage
sudo journalctl -u subscription
```

## رفع مشکلات رایج

1. خطای دسترسی به پایگاه داده:
```bash
sudo chmod 777 /usr/local/s-ui/db/s-ui.db
```

2. خطای دسترسی به پورت 80/443:
```bash
sudo lsof -i :80
sudo lsof -i :443
```

3. مشکل SSL:
```bash
sudo certbot --nginx -d yourdomain.com
```
```
