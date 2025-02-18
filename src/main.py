import mysql.connector
import json
import uuid
import base64
import secrets
import requests
from typing import Dict, List, Optional

class UserSyncAPI:
    def __init__(self, config_path: str = '/opt/sui-sync/config.json'):
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.db_config = config['database']['xmplus']
        self.server_ip = config['server_ip']
        self.api_url = "http://localhost:2095/app/apiv2/save"
        self.api_token = config['api_token']
        self.obfs_password = config['obfs_password']

    def _connect_xmplus(self) -> mysql.connector.MySQLConnection:
        return mysql.connector.connect(**self.db_config)

    def _generate_config(self, username: str, token: str) -> Dict:
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
        return [{
            "remark": f"hysteria2-{port}",
            "type": "local",
            "uri": f"hysteria2://{token}@{self.server_ip}:{port}?fastopen=0&obfs=salamander&obfs-password={self.obfs_password}#{username}"
        }]

    def _add_user(self, username: str, token: str) -> bool:
        config = self._generate_config(username, token)
        links = self._generate_hy2_link(username, token)

        data = {
            "enable": True,
            "name": username,
            "config": config,
            "inbounds": [3, 4, 5],
            "links": links,
            "volume": 0,
            "expiry": 0,
            "up": 0,
            "down": 0,
            "desc": "",
            "group": ""
        }

        headers = {
            'Token': self.api_token
        }

        files = {
            'object': (None, 'clients'),
            'action': (None, 'new'),
            'data': (None, json.dumps(data))
        }

        try:
            response = requests.post(self.api_url, headers=headers, files=files)
            response.raise_for_status()
            print(f"User {username} added successfully via API")
            return True
        except Exception as e:
            print(f"Error adding user {username}: {e}")
            return False

    def _remove_user(self, username: str) -> bool:
        headers = {
            'Token': self.api_token
        }

        files = {
            'object': (None, 'clients'),
            'action': (None, 'del'),
            'data': (None, json.dumps({"name": username}))
        }

        try:
            response = requests.post(self.api_url, headers=headers, files=files)
            response.raise_for_status()
            print(f"User {username} removed successfully via API")
            return True
        except Exception as e:
            print(f"Error removing user {username}: {e}")
            return False

    def _get_current_users(self) -> List[str]:
        url = "http://localhost:2095/app/apiv2/list"
        headers = {'Token': self.api_token}
        files = {'object': (None, 'clients')}

        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            clients = response.json().get('obj', [])
            return [client['name'] for client in clients]
        except Exception as e:
            print(f"Error getting current users: {e}")
            return []

    def sync_users(self) -> tuple[int, int]:
        try:
            # Get active tokens from xmplus
            with self._connect_xmplus() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT uuid FROM service WHERE status = 1 AND traffic - total_used > 10000")
                active_tokens = {user['uuid'] for user in cursor.fetchall()}

            # Get current users from API
            current_users = set(self._get_current_users())

            # Find users to remove
            users_to_remove = current_users - active_tokens
            removed_count = 0
            for username in users_to_remove:
                if self._remove_user(username):
                    removed_count += 1

            # Add new users
            users_to_add = active_tokens - current_users
            added_count = 0
            for token in users_to_add:
                if self._add_user(token, token):
                    added_count += 1

            print(f"Added {added_count} new users, removed {removed_count} invalid users")
            return added_count, removed_count

        except Exception as e:
            print(f"Error in sync_users: {e}")
            return 0, 0

def main():
    import time

    syncer = UserSyncAPI()
    print("Starting user synchronization...")
    added, removed = syncer.sync_users()
    print(f"Synchronization completed: {added} users added, {removed} users removed")

if __name__ == "__main__":
    main()