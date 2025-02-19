import mysql.connector
import time
import logging
import json
import requests
from typing import List, Dict, Optional, Tuple

class TrafficSync:
    def __init__(self):
        with open('/root/xmplus-hysteria2/config.json', 'r') as f:
            config = json.load(f)

        self.db_config = config.get('database').get('xmplus')
        self.api_token = config.get('api_token')
        self.api_base_url = "http://localhost:2095/app/apiv2"
        self._setup_logging()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('traffic_sync.log'),
                logging.StreamHandler()
            ]
        )

    def _connect_xmplus(self) -> Optional[mysql.connector.MySQLConnection]:
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as e:
            logging.error(f"Failed to connect to XMPlus: {e}")
            return None

    def _get_traffic_data(self) -> List[Dict]:
        url = f"{self.api_base_url}/clients"
        headers = {'Token': self.api_token}

        try:
            response = requests.get(url, headers=headers)
            logging.debug(f"Get clients response: {response.text}")
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                logging.error(f"API returned error: {data.get('msg')}")
                return []

            clients = data.get('obj', {}).get('clients', [])
            if not clients:
                logging.info("No clients found")
                return []

            # فیلتر کردن کلاینت‌های با ترافیک و حفظ همه اطلاعات آنها
            filtered_clients = []
            for client in clients:
                if client.get('down', 0) > 0 or client.get('up', 0) > 0:
                    logging.debug(f"Original client data: {json.dumps(client)}")
                    filtered_clients.append(client)

            return filtered_clients

        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting traffic data: {e}")
            return []

    def _get_client_details(self, client_id: int) -> Optional[Dict]:
        """Get complete client details including config"""
        url = f"{self.api_base_url}/client/{client_id}"
        headers = {'Token': self.api_token}

        try:
            response = requests.get(url, headers=headers)
            logging.debug(f"Get client details response: {response.text}")
            data = response.json()

            if data.get('success'):
                return data.get('obj')
            else:
                logging.error(f"Failed to get client details: {data.get('msg')}")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting client details: {e}")
            return None

    def _reset_traffic(self, client_data: Dict) -> bool:
        """Reset traffic for a specific client using API"""
        url = f"{self.api_base_url}/save"
        headers = {'Token': self.api_token}

        # بازسازی ساختار کامل کلاینت با تنظیمات پیش‌فرض
        reset_data = {
            "id": client_data['id'],
            "enable": client_data.get('enable', True),
            "name": client_data['name'],
            "config": {
                "mixed": {
                    "username": client_data['name'],
                    "password": client_data['name']
                },
                "socks": {
                    "username": client_data['name'],
                    "password": client_data['name']
                },
                "http": {
                    "username": client_data['name'],
                    "password": client_data['name']
                },
                "shadowsocks": {
                    "name": client_data['name'],
                    "password": "default_password"
                },
                "shadowsocks16": {
                    "name": client_data['name'],
                    "password": "default_password"
                },
                "shadowtls": {
                    "name": client_data['name'],
                    "password": "default_password"
                },
                "vmess": {
                    "name": client_data['name'],
                    "uuid": "default_uuid",
                    "alterId": 0
                },
                "vless": {
                    "name": client_data['name'],
                    "uuid": "default_uuid",
                    "flow": "xtls-rprx-vision"
                },
                "trojan": {
                    "name": client_data['name'],
                    "password": client_data['name']
                },
                "naive": {
                    "username": client_data['name'],
                    "password": client_data['name']
                },
                "hysteria": {
                    "name": client_data['name'],
                    "auth_str": client_data['name']
                },
                "tuic": {
                    "name": client_data['name'],
                    "uuid": "default_uuid",
                    "password": client_data['name']
                },
                "hysteria2": {
                    "name": client_data['name'],
                    "password": client_data['name']
                }
            },
            "inbounds": client_data.get('inbounds', [1]),
            "links": client_data.get('links', []),
            "volume": client_data.get('volume', 0),
            "expiry": client_data.get('expiry', 0),
            "up": 0,
            "down": 0,
            "desc": client_data.get('desc', ''),
            "group": client_data.get('group', '')
        }

        files = {
            'object': (None, 'clients'),
            'action': (None, 'edit'),
            'data': (None, json.dumps(reset_data))
        }

        logging.debug(f"Reset traffic request data: {json.dumps(reset_data)}")

        try:
            response = requests.post(url, headers=headers, files=files)
            logging.debug(f"Reset traffic response: {response.text}")
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                logging.info(f"Reset traffic for client {client_data['name']}")
                return True
            else:
                logging.error(f"Failed to reset traffic for client {client_data['name']}: {result.get('msg')}")
                return False

        except requests.exceptions.RequestException as e:
            logging.error(f"Error resetting traffic for client {client_data['name']}: {e}")
            return False

    def _update_xmplus_traffic(self, token: str, down: int, up: int) -> bool:
        with self._connect_xmplus() as conn:
            if not conn:
                return False

            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE service
                    SET u = u + %s,
                        d = d + %s,
                        total_used = total_used + %s
                    WHERE uuid = %s
                """, (up, down, up + down, token))

                conn.commit()
                return cursor.rowcount > 0

            except mysql.connector.Error as e:
                logging.error(f"Error updating traffic for {token}: {e}")
                return False

    def sync_traffic(self) -> int:
        logging.info("Starting traffic synchronization")

        traffic_data = self._get_traffic_data()
        updated_count = 0

        for client in traffic_data:
            token = client['name']
            down = client.get('down', 0)
            up = client.get('up', 0)

            if down > 0 or up > 0:
                logging.info(f"Processing {token}: UP={up}, DOWN={down}")
                try:
                    # اول در xmplus آپدیت می‌کنیم
                    if self._update_xmplus_traffic(token, down, up):
                        # اگر موفق بود، در s-ui ریست می‌کنیم
                        if self._reset_traffic(client):
                            updated_count += 1
                            logging.info(f"Successfully updated and reset traffic for {token}")
                        else:
                            logging.error(f"Failed to reset traffic in s-ui for {token}")
                    else:
                        logging.error(f"Failed to update traffic in XMPlus for {token}")
                except Exception as e:
                    logging.error(f"Error processing {token}: {e}")
                    continue

        logging.info(f"Sync completed. Successfully updated {updated_count} users")
        return updated_count

def main():
    syncer = TrafficSync()

    try:
        syncer.sync_traffic()
    except Exception as e:
        logging.error(f"Critical error in sync process: {e}")

    logging.info("Sync completed")

if __name__ == "__main__":
    main()