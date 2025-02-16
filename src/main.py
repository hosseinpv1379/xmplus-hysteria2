import sqlite3
import mysql.connector
import json
import uuid
import base64
import secrets
from typing import Dict, List, Optional
import json

with open('/opt/sui-sync/config.json', 'r') as f:
    config = json.load(f)

SUI_DB_PATH = config['sui_db_path']
DB_CONFIG = config['database']['xmplus']
SERVER_IP = config['server_ip']
OBFS_PASSWORD = config['obfs_password']

class UserSync:
    def __init__(self ):
        self.sui_db_path = SUI_DB_PATH
        self.server_ip = SERVER_IP
        self.db_config = DB_CONFIG
        self.obfs_password = OBFS_PASSWORD

    def _connect_xmplus(self) -> mysql.connector.MySQLConnection:
        return mysql.connector.connect(**self.db_config)

    def _connect_sui(self) -> sqlite3.Connection:
        return sqlite3.connect(self.sui_db_path)

    def _get_active_users(self) -> List[Dict]:
        with self._connect_xmplus() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT uuio FROM service WHERE status = 1 AND traffic - total_used > 10000")
            return cursor.fetchall()

    def _user_exists(self, username: str) -> bool:
        with self._connect_sui() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clients WHERE name = ?", (username,))
            return cursor.fetchone() is not None

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
            print(f"User {username} already exists in s-ui")
            return False

        config = self._generate_config(username, token)
        links = self._generate_hy2_link(username, token)
        
        try:
            with self._connect_sui() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO clients (enable, name, config, inbounds, links, volume, expiry, down, up, desc, `group`)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    1, username, 
                    json.dumps(config, indent=2).encode(),
                    json.dumps([1], indent=2).encode(),
                    json.dumps(links, indent=2).encode(),
                    0, 0, 0, 0, '', ''
                ))
                conn.commit()
                print(f"User {username} added successfully to s-ui")
                return True
                
        except Exception as e:
            print(f"Error adding user {username}: {e}")
            return False

# Replace the old sync_users method with this new one
    def sync_users(self) -> tuple[int, int]:
        """
        Syncs users and removes invalid tokens from s-ui.
        Returns tuple of (added_count, removed_count)
        """
        try:
            # Get active tokens from xmplus
            with self._connect_xmplus() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT uuid FROM service WHERE status = 1 AND traffic - total_used > 10000")
                active_tokens = {user['uuid'] for user in cursor.fetchall()}

            # Get current tokens from s-ui
            with self._connect_sui() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM clients")
                sui_tokens = {row[0] for row in cursor.fetchall()}

            # Find tokens to remove (in s-ui but not in xmplus)
            tokens_to_remove = sui_tokens - active_tokens

            # Remove invalid tokens from s-ui
            removed_count = 0
            if tokens_to_remove:
                with self._connect_sui() as conn:
                    cursor = conn.cursor()
                    for token in tokens_to_remove:
                        cursor.execute("DELETE FROM clients WHERE name = ?", (token,))
                        removed_count += cursor.rowcount
                    conn.commit()

            # Add new tokens from xmplus
            added_count = 0
            tokens_to_add = active_tokens - sui_tokens
            for token in tokens_to_add:
                if self._add_user(token, token):  # Using token as both username and token
                    added_count += 1

            print(f"Added {added_count} new users, removed {removed_count} invalid users")
            return added_count, removed_count

        except Exception as e:
            print(f"Error in sync_users: {e}")
            return 0, 0

def main():
    import subprocess
    import time

    syncer = UserSync()
    print("Starting user synchronization...")
    added, removed = syncer.sync_users()
    print(f"Synchronization completed: {added} users added, {removed} users removed")

    # Restart s-ui service
    try:
        print("Restarting s-ui service...")
        subprocess.run(['systemctl', 'restart', 's-ui'], check=True)
        time.sleep(2)  # Wait for 2 seconds
        
        # Check if service is running
        status = subprocess.run(['systemctl', 'is-active', 's-ui'], 
                              capture_output=True, 
                              text=True)
        
        if status.stdout.strip() == 'active':
            print("s-ui service restarted successfully")
        else:
            print("Warning: s-ui service might not have restarted properly")
            
    except subprocess.CalledProcessError as e:
        print(f"Error restarting s-ui service: {e}")

if __name__ == "__main__":
    main()
