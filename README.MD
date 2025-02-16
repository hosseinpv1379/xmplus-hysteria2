# VPN Service Installation Guide

## Prerequisites
- Ubuntu 20.04 or higher
- Root access
- Domain pointed to your server
- S-UI and XMPlus panels already installed

## Quick Installation

```bash
git clone https://github.com/hosseinpv1379/xmplus-hysteria2.git

cd xmplus-hysteria2
sudo bash install.sh
```

2. Edit `config.json`:
```json
{
  "database": {
    "sui_db_path": "/usr/local/s-ui/db/s-ui.db",
    "xmplus": {
      "host": "your_db_host",
      "user": "your_db_user",
      "password": "your_db_password",
      "database": "your_db_name"
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
        "ip": "your_server_ip",
        "port": 443,
        "obfs": "salamander",
        "obfs_password": "your_obfs_password"
      }
    ]
  }
}
```

3. Run the installation script:
```bash
sudo bash install.sh
```

4. During installation, you'll be prompted for:
   - Domain name
   - Database credentials
   - Server configurations
   - Service names

## Service Management

Check services status:
```bash
sudo systemctl status sync-users
sudo systemctl status sync-usage
sudo systemctl status subscription
```

View logs:
```bash
sudo journalctl -u sync-users -f
sudo journalctl -u sync-usage -f
sudo journalctl -u subscription -f
```

Restart services:
```bash
sudo systemctl restart sync-users
sudo systemctl restart sync-usage
sudo systemctl restart subscription
```

## Troubleshooting

### Database Access Error
If you encounter database access issues:
```bash
sudo chmod 777 /usr/local/s-ui/db/s-ui.db
sudo chown -R root:root /usr/local/s-ui/db/
```

### Port Access Issues
Check if ports 80/443 are in use:
```bash
sudo lsof -i :80
sudo lsof -i :443
```

### SSL Certificate Issues
Manually renew SSL certificate:
```bash
sudo certbot --nginx -d yourdomain.com
```

### Nginx Configuration
Check Nginx configuration:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

## API Endpoints

### Subscription Link
```
https://yourdomain.com/link/<token>?client=<client_name>
```

Example:
```
https://yourdomain.com/link/abc123?client=client1
```

## Security Recommendations

1. Configure firewall:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

2. Secure database access:
```bash
sudo chmod 640 /usr/local/s-ui/db/s-ui.db
```

3. Regular updates:
```bash
sudo apt update
sudo apt upgrade
```

## Updating the Service

1. Stop services:
```bash
sudo systemctl stop sync-users sync-usage subscription
```

2. Update files:
```bash
cd /opt/sui-sync
git pull origin main
```

3. Restart services:
```bash
sudo systemctl restart sync-users sync-usage subscription
```

## Backup and Recovery

1. Backup configuration:
```bash
sudo cp /opt/sui-sync/config.json /opt/sui-sync/config.backup.json
```

2. Backup database:
```bash
sudo cp /usr/local/s-ui/db/s-ui.db /usr/local/s-ui/db/s-ui.backup.db
```

## Support

For issues and feature requests, please create an issue on GitHub repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

This comprehensive guide should help users install and maintain the service effectively. Let me know if you need any clarification or additional sections!
