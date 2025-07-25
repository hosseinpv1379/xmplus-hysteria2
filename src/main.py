import mysql.connector
import json
import uuid
import base64
import secrets
import requests
import traceback
from typing import Dict, List, Optional

class UserSyncAPI:
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
        if self._user_exists(username):
            print(f"User {username} already exists")
            return False

        config = self._generate_config(username, token)
        links = self._generate_hy2_link(username, token)

        data = {
            "enable": True,
            "name": username,
            "config": config,
            "inbounds": [1],  # اعداد باید به صورت عددی باشند
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
            'data': (None, json.dumps([{  # تبدیل به لیست با یک آبجکت
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
            }]))
        }

        try:
            headers = {
                'Token': self.api_token
            }

            files = {
                'object': (None, 'clients'),
                'action': (None, 'new'),
                'data': (None, json.dumps(data))
            }

            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                #print(f"User {username} added successfully via API")
                return True
            else:
                print(f"Failed to add user {username}: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"Error adding user {username}: {e}")
            return False

    def _get_user_id(self, username: str) -> Optional[int]:
        current_users = self._get_current_users()
        for user in current_users:
            if user['name'] == username:
                return user['id']
        return None

    def _remove_user(self, username: str) -> bool:
        user_id = self._get_user_id(username)
        if user_id is None:
            #print(f"User {username} not found")
            return False

        headers = {
            'Token': self.api_token
        }

        files = {
            'object': (None, 'clients'),
            'action': (None, 'del'),
            'data': (None, str(user_id))  # فقط ID به صورت عددی
        }

        try:
            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                #print(f"User {username} removed successfully via API")
                return True
            else:
                #print(f"Failed to remove user {username}: {result.get('msg')}")
                return False
        except Exception as e:
            #print(f"Error removing user {username}: {e}")
            return False

        try:
            response = requests.post(self.api_save_url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                print(f"User {username} removed successfully via API")
                return True
            else:
                print(f"Failed to remove user {username}: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"Error removing user {username}: {e}")
            return False

    def _get_current_users(self) -> List[Dict]:
        headers = {'Token': self.api_token}

        try:
            response = requests.get(self.api_clients_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                #print(f"API returned error: {data.get('msg')}")
                return []

            clients = data.get('obj', {}).get('clients')
            if clients is None:
                #print("No clients found in s-ui")
                return []

            return clients

        except requests.exceptions.RequestException as e:
            #print(f"HTTP Error: {e}")
            return []
        except json.JSONDecodeError as e:
            #print(f"JSON Parse Error: {e}")
            return []
        except Exception as e:
            #print(f"Unexpected Error: {e}")
            traceback.print_exc()
            return []

    def sync_users(self) -> tuple[int, int]:
        try:
            #print("Getting active UUIDs from xmplus...")
            with self._connect_xmplus() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT uuid FROM service WHERE status = 1 AND traffic - total_used > 200000000 LIMIT 500")
                active_uuids = {user['uuid'] for user in cursor.fetchall()}
            #print(f"Found {len(active_uuids)} active UUIDs in xmplus")

            #print("Getting current users from s-ui...")
            current_users = self._get_current_users()
            current_uuids = set()

            # اضافه کردن تمام uuid های موجود در s-ui
            if current_users:
                for user in current_users:
                    try:
                        if user and isinstance(user, dict) and 'name' in user:
                            current_uuids.add(user['name'])
                    except Exception as e:
                        #print(f"Error processing user {user}: {e}")
                        continue

            #print(f"Found {len(current_uuids)} users in s-ui")

            # کاربرانی که باید حذف شوند
            to_remove = current_uuids - active_uuids
            print(f"Found {len(to_remove)} users to remove")

            # کاربرانی که باید اضافه شوند
            to_add = active_uuids - current_uuids
            print(f"Found {len(to_add)} users to add")

            # حذف کاربران غیر فعال
            removed_count = 0
            for uuid in to_remove:
                try:
                    #print(f"Removing user {uuid}...")
                    if self._remove_user(uuid):
                        removed_count += 1
                    else:
                        print(f"Failed to remove user {uuid}")
                except Exception as e:
                    print(f"Error removing user {uuid}: {e}")
                    continue

            # اضافه کردن کاربران جدید
            added_count = 0
            for uuid in to_add:
                try:
                    #print(f"Adding user {uuid}...")
                    if self._add_user(uuid, uuid):
                        added_count += 1
                    else:
                        print(f"Failed to add user {uuid}")
                except Exception as e:
                    print(f"Error adding user {uuid}: {e}")
                    continue

            print(f"Sync completed: Added {added_count} users, Removed {removed_count} users")
            return added_count, removed_count

        except Exception as e:
            print(f"Error in sync_users: {e}")
            traceback.print_exc()
            return 0, 0

    def _user_exists(self, username: str) -> bool:
        current_users = self._get_current_users()
        return any(user['name'] == username for user in current_users)

    def sync_users(self) -> tuple[int, int]:
        try:
            print("Getting active UUIDs from xmplus...")
            # فقط uuid های اکتیو و با ترافیک باقیمانده
            with self._connect_xmplus() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT uuid FROM service WHERE status = 1 AND traffic - total_used > 200000000")
                active_uuids = {user['uuid'] for user in cursor.fetchall()}
            print(f"Found {len(active_uuids)} active UUIDs in xmplus")

            print("Getting current users from s-ui...")
            # تمام کاربران موجود در s-ui
            current_users = self._get_current_users()
            current_uuids = {user['name'] for user in current_users}
            print(f"Found {len(current_uuids)} users in s-ui")

            # کاربرانی که باید حذف شوند
            to_remove = current_uuids - active_uuids
            print(f"Found {len(to_remove)} users to remove")

            # کاربرانی که باید اضافه شوند
            to_add = active_uuids - current_uuids
            print(f"Found {len(to_add)} users to add")

            # حذف کاربران غیر فعال
            removed_count = 0
            for uuid in to_remove:
                print(f"Removing user {uuid}...")
                if self._remove_user(uuid):
                    removed_count += 1

            # اضافه کردن کاربران جدید
            added_count = 0
            for uuid in to_add:
                print(f"Adding user {uuid}...")
                if self._add_user(uuid, uuid):
                    added_count += 1

            print(f"Sync completed: Added {added_count} users, Removed {removed_count} users")
            return added_count, removed_count

        except Exception as e:
            print(f"Error in sync_users: {e}")
            traceback.print_exc()
            return 0, 0

def main():
    import time

    syncer = UserSyncAPI()
    print("Starting user synchronization...")
    added, removed = syncer.sync_users()
    print(f"Synchronization completed: {added} users added, {removed} users removed")

if __name__ == "__main__":
    main()