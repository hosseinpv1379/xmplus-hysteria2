import sqlite3
import mysql.connector
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging
import subprocess
import json

with open('/opt/sui-sync/config.json', 'r') as f:
    config = json.load(f)
    
SUI_DB_PATH = config['sui_db_path']
DB_CONFIG = config['xmplus_db']
SERVER_IP = config['server_ip']
OBFS_PASSWORD = config['obfs_password']
class TrafficSync:
    def __init__(self, sui_path = SUI_DB_PATH):
        self.sui_db_path = sui_path
        self.db_config = DB_CONFIG
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging for the application"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('traffic_sync.log'),
                logging.StreamHandler()
            ]
        )

    def _connect_sui(self) -> Optional[sqlite3.Connection]:
        """Connect to s-ui SQLite database"""
        try:
            return sqlite3.connect(self.sui_db_path)
        except sqlite3.Error as e:
            logging.error(f"Failed to connect to s-ui: {e}")
            return None

    def _connect_xmplus(self) -> Optional[mysql.connector.MySQLConnection]:
        """Connect to XMPlus MySQL database"""
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as e:
            logging.error(f"Failed to connect to XMPlus: {e}")
            return None

    def _get_and_reset_traffic(self) -> List[Tuple[str, int, int]]:
        """Get and reset traffic data from s-ui"""
        with self._connect_sui() as conn:
            if not conn:
                return []
            
            cursor = conn.cursor()
            try:
                # Get current traffic data
                cursor.execute("""
                    SELECT name, down, up 
                    FROM clients 
                    WHERE down > 0 OR up > 0
                """)
                traffic_data = cursor.fetchall()
                
                # Reset traffic counters
                cursor.execute("""
                    UPDATE clients 
                    SET down = 0, up = 0 
                    WHERE down > 0 OR up > 0
                """)
                conn.commit()
                
                return traffic_data
                
            except sqlite3.Error as e:
                logging.error(f"Error in traffic data operation: {e}")
                return []

    def _update_xmplus_traffic(self, token: str, down: int, up: int) -> bool:
        """Update traffic data in XMPlus"""
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
        """Synchronize traffic between s-ui and XMPlus"""
        logging.info("Starting traffic synchronization")
        
        traffic_data = self._get_and_reset_traffic()
        updated_count = 0
        
        for token, down, up in traffic_data:
            if down > 0 or up > 0:
                logging.info(f"Updating traffic for {token}: UP={up}, DOWN={down}")
                if self._update_xmplus_traffic(token, down, up):
                    updated_count += 1
        
        logging.info(f"Sync completed. Updated {updated_count} users")
        return updated_count

def main():
    syncer = TrafficSync()
    
    try:
        syncer.sync_traffic()
    except Exception as e:
        logging.error(f"Critical error in sync process: {e}")
    
    logging.info("Waiting for next sync cycle...")
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
