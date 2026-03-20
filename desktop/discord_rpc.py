import time
import threading
import logging
from pypresence import Presence

logger = logging.getLogger(__name__)

# Replace with an actual Discord Application ID named "Streamore"
DISCORD_CLIENT_ID = '1351662973165314058' 

class DiscordRPCManager:
    def __init__(self, client_id=DISCORD_CLIENT_ID):
        self.client_id = client_id
        self.rpc = None
        self.connected = False
        self.last_update = 0
        
        self._thread = threading.Thread(target=self._connect_loop, daemon=True)
        self._thread.start()
        
    def _connect_loop(self):
        while True:
            if not self.connected:
                try:
                    self.rpc = Presence(self.client_id)
                    self.rpc.connect()
                    self.connected = True
                    logger.info("Connected to Discord RPC")
                    
                    # Initial state
                    self.rpc.update(state="Idle", details="Browsing catalog", large_text="Streamore")
                except Exception as e:
                    logger.debug(f"Failed to connect to Discord RPC (is Discord open?): {e}")
                    self.connected = False
                    self.rpc = None
                    
            time.sleep(15)  # Reconnect backoff / keep alive
            
    def update(self, downloads: list):
        if not self.connected or not self.rpc:
            return
            
        now = time.time()
        # Rate limit Discord API updates to once every 5 seconds to avoid bans
        if (now - self.last_update) < 5.0:
            return
            
        try:
            active = [d for d in downloads if (d.get('state', '') or '').lower() in ('downloading', 'active')]
            if len(active) > 0:
                top = active[0]
                title = top.get('movie_title') or top.get('name') or 'Download'
                prog = float(top.get('progress', 0) or 0)
                
                details = f"Downloading: {title}"
                state = f"Progress: {prog:.1f}%"
                if len(active) > 1:
                    state += f" (+{len(active)-1} more)"
                
                self.rpc.update(
                    state=state,
                    details=details,
                    large_text="Streamore Download Manager"
                )
            else:
                self.rpc.update(
                    state="Idle",
                    details="Browsing Streamore",
                    large_text="Streamore Download Manager"
                )
            
            self.last_update = now
        except Exception as e:
            logger.debug(f"Failed to update Discord RPC: {e}")
            self.connected = False
            self.rpc = None
