import mysql.connector
import json
import uuid
import base64
import secrets
import requests
import traceback
import logging
from typing import Dict, List, Optional, Tuple

class UnifiedSyncAPI:
    def __init__(self, config_path: str = '/root/xmplus-hysteria2/config.json'):
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.db_config = config['database']['xmplus']
        self.server_ip = config['server_ip']
        self.api_base_url = "http://localhost:2095/app/apiv2"
        self.api_save_url = f"{self.api_base_url}/save"
        self.api_clients_url = f"{self.api_base_url}/clients"
        self.api_token = config['api_token']
        self.obfs_password = config['obfs_password']
        self._setup_logging()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.ERROR,  # فقط خطاها نمایش داده شوند
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('sync.log'),
                logging.StreamHandler()
            ]
        )

    def _connect_xmplus(self) -> Optional[mysql.connector.MySQLConnection]:
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as e:
            logging.error(f"Failed to connect to XMPlus: {e}")
            return None

    def _get_current_users(self) -> List[Dict]:
        headers = {'Token': self.api_token}
        try:
            response = requests.get(self.api_clients_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                return []

            clients = data.get('obj', {}).get('clients')
            return clients if clients else []

        except Exception as e:
            logging.error(f"Error getting current users: {e}")
            return []

    def _get_traffic_data(self) -> List[Dict]:
        """Get clients with traffic data"""
        clients = self._get_current_users()
        return [client for client in clients if client.get('down', 0) > 0 or client.get('up', 0) > 0]

    def _update_xmplus_traffic(self, token: str, down: int, up: int) -> bool:
        """Update traffic in XMPlus database"""
        conn = self._connect_xmplus()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            up_value = int(up / 0.8)
            down_value = int(down / 0.8)
            total_value = up_value + down_value

            cursor.execute("""
                UPDATE service
                SET u = u + %s,
                    d = d + %s,
                    total_used = total_used + %s
                WHERE uuid = %s
            """, (up_value, down_value, total_value, token))

            conn.commit()
            return cursor.rowcount > 0

        except mysql.connector.Error as e:
            logging.error(f"Error updating traffic for {token}: {e}")
            return False
        finally:
            conn.close()

    def _reset_traffic(self, client_data: Dict) -> bool:
        """Reset traffic for a specific client using API"""
        headers = {'Token': self.api_token}

        reset_data = {
            "id": client_data['id'],
            "enable": client_data.get('enable', True),
            "name": client_data['name'],
            "config": client_data.get('config', self._generate_config(client_data['name'], client_data['name'])),
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

        try:
            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            return result.get('success', False)

        except Exception as e:
            logging.error(f"Error resetting traffic for {client_data['name']}: {e}")
            return False

    def _generate_config(self, username: str, token: str) -> Dict:
        """Generate client configuration"""
        client_uuid = str(uuid.uuid4())
        ss_password = base64.b64encode(secrets.token_bytes(32)).decode()
        ss16_password = base64.b64encode(secrets.token_bytes(16)).decode()

        return {
            "mixed": {"username": username, "password": token},
            "socks": {"username": username, "password": token},
            "http": {"username": username, "password": token},
            "shadowsocks": {"name": username, "password": ss_password},
            "shadowsocks16": {"name": username, "password": ss16_password},
            "shadowtls": {"name": username, "password": ss_password},
            "vmess": {"name": username, "uuid": client_uuid, "alterId": 0},
            "vless": {"name": username, "uuid": client_uuid, "flow": "xtls-rprx-vision"},
            "trojan": {"name": username, "password": token},
            "naive": {"username": username, "password": token},
            "hysteria": {"name": username, "auth_str": token},
            "tuic": {"name": username, "uuid": client_uuid, "password": token},
            "hysteria2": {"name": username, "password": token}
        }

    def _generate_hy2_link(self, username: str, token: str, port: int = 443) -> List[Dict]:
        """Generate Hysteria2 link"""
        return [{
            "remark": f"hysteria2-{port}",
            "type": "local",
            "uri": f"hysteria2://{token}@{self.server_ip}:{port}?fastopen=0&obfs=salamander&obfs-password={self.obfs_password}#{username}"
        }]

    def _add_user(self, username: str, token: str) -> bool:
        """Add new user via API"""
        config = self._generate_config(username, token)
        links = self._generate_hy2_link(username, token)

        data = {
            "enable": True,
            "name": username,
            "config": config,
            "inbounds": [1],
            "links": links,
            "volume": 0,
            "expiry": 0,
            "up": 0,
            "down": 0,
            "desc": "",
            "group": ""
        }

        headers = {'Token': self.api_token}
        files = {
            'object': (None, 'clients'),
            'action': (None, 'new'),
            'data': (None, json.dumps(data))
        }

        try:
            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            logging.error(f"Error adding user {username}: {e}")
            return False

    def _get_user_id(self, username: str) -> Optional[int]:
        """Get user ID by username"""
        current_users = self._get_current_users()
        for user in current_users:
            if user.get('name') == username:
                return user.get('id')
        return None

    def _remove_user(self, username: str) -> bool:
        """Remove user via API"""
        user_id = self._get_user_id(username)
        if user_id is None:
            return False

        headers = {'Token': self.api_token}
        files = {
            'object': (None, 'clients'),
            'action': (None, 'del'),
            'data': (None, str(user_id))
        }

        try:
            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            logging.error(f"Error removing user {username}: {e}")
            return False

    def sync_traffic(self) -> int:
        """Sync traffic from s-ui to XMPlus and reset s-ui counters"""
        traffic_data = self._get_traffic_data()
        updated_count = 0

        for client in traffic_data:
            token = client['name']
            down = client.get('down', 0)
            up = client.get('up', 0)

            if down > 0 or up > 0:
                try:
                    if self._update_xmplus_traffic(token, down, up):
                        if self._reset_traffic(client):
                            updated_count += 1
                        else:
                            logging.error(f"Failed to reset traffic in s-ui for {token}")
                    else:
                        logging.error(f"Failed to update traffic in XMPlus for {token}")
                except Exception as e:
                    logging.error(f"Error processing traffic for {token}: {e}")
                    continue

        return updated_count

    def sync_users(self) -> Tuple[int, int]:
        """Sync users between XMPlus and s-ui"""
        try:
            # Get active UUIDs from XMPlus
            conn = self._connect_xmplus()
            if not conn:
                return 0, 0

            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT uuid FROM service WHERE status = 1 AND traffic - total_used > 200000000 LIMIT 500")
                active_uuids = {user['uuid'] for user in cursor.fetchall()}
            finally:
                conn.close()

            # Get current users from s-ui
            current_users = self._get_current_users()
            current_uuids = {user['name'] for user in current_users if user.get('name')}

            # Calculate differences
            to_remove = current_uuids - active_uuids
            to_add = active_uuids - current_uuids

            # Remove inactive users
            removed_count = 0
            for uuid in to_remove:
                try:
                    if self._remove_user(uuid):
                        removed_count += 1
                    else:
                        logging.error(f"Failed to remove user {uuid}")
                except Exception as e:
                    logging.error(f"Error removing user {uuid}: {e}")

            # Add new users
            added_count = 0
            for uuid in to_add:
                try:
                    if self._add_user(uuid, uuid):
                        added_count += 1
                    else:
                        logging.error(f"Failed to add user {uuid}")
                except Exception as e:
                    logging.error(f"Error adding user {uuid}: {e}")

            return added_count, removed_count

        except Exception as e:
            logging.error(f"Error in sync_users: {e}")
            return 0, 0

    def full_sync(self) -> Dict[str, int]:
        """Perform complete synchronization: traffic first, then users"""
        print("Starting synchronization...")

        # Step 1: Sync traffic
        traffic_updated = self.sync_traffic()

        # Step 2: Sync users
        users_added, users_removed = self.sync_users()

        # Summary report
        results = {
            'traffic_updated': traffic_updated,
            'users_added': users_added,
            'users_removed': users_removed
        }

        print(f"Sync completed - Traffic updated: {traffic_updated}, Users added: {users_added}, Users removed: {users_removed}")
        return results

def main():
    try:
        syncer = UnifiedSyncAPI()
        syncer.full_sync()
    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        print(f"Sync failed: {e}")

if __name__ == "__main__":
    logging.info("Starting main synchronization process")
    main()