import csv
import os
import requests
import time
import datetime
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class ProxyRotator:
    """Manages proxy rotation and health checking"""
    
    def __init__(self, proxies_file: Optional[Path] = None):
        self.proxies_file = proxies_file or Path("proxies.csv")
        self.proxies = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.proxy_stats = {}
        self.load_proxies()
        
    def load_proxies(self):
        """Load proxies from CSV file or environment variables"""
        # Try loading from CSV file first
        if self.proxies_file.exists():
            self._load_from_csv()
        else:
            # Fallback to environment variables
            self._load_from_env()
            
        if not self.proxies:
            logger.warning("No proxies configured, using direct connection")
        else:
            logger.info(f"Loaded {len(self.proxies)} proxies")
            
    def _load_from_csv(self):
        """Load proxies from CSV file format: ip,port,login,password,type"""
        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    proxy_config = {
                        'ip': row.get('ip', '').strip(),
                        'port': row.get('port', '').strip(),
                        'login': row.get('login', '').strip(),
                        'password': row.get('password', '').strip(),
                        'type': row.get('type', 'http').strip().lower()
                    }
                    
                    if proxy_config['ip'] and proxy_config['port']:
                        self.proxies.append(proxy_config)
                        self.proxy_stats[self._get_proxy_key(proxy_config)] = {
                            'success_count': 0,
                            'failure_count': 0,
                            'last_used': None,
                            'response_time': []
                        }
                        
        except Exception as e:
            logger.error(f"Error loading proxies from CSV: {e}")
            
    def _load_from_env(self):
        """Load single proxy from environment variables"""
        proxy_login = os.getenv("PROXY_LOGIN")
        proxy_password = os.getenv("PROXY_PASS") 
        proxy_ip = os.getenv("PROXY_IP")
        proxy_port = os.getenv("PROXY_PORT")
        proxy_type = os.getenv("PROXY_TYPE", "http")
        
        if all([proxy_ip, proxy_port]):
            proxy_config = {
                'ip': proxy_ip,
                'port': proxy_port,
                'login': proxy_login or '',
                'password': proxy_password or '',
                'type': proxy_type.lower()
            }
            self.proxies.append(proxy_config)
            self.proxy_stats[self._get_proxy_key(proxy_config)] = {
                'success_count': 0,
                'failure_count': 0,
                'last_used': None,
                'response_time': []
            }
            
    def _get_proxy_key(self, proxy_config: Dict) -> str:
        """Generate unique key for proxy"""
        return f"{proxy_config['ip']}:{proxy_config['port']}"
        
    def _build_proxy_url(self, proxy_config: Dict) -> str:
        """Build proxy URL from configuration"""
        auth = ""
        if proxy_config['login'] and proxy_config['password']:
            auth = f"{proxy_config['login']}:{proxy_config['password']}@"
            
        return f"{proxy_config['type']}://{auth}{proxy_config['ip']}:{proxy_config['port']}"
        
    def get_current_proxy(self) -> Dict[str, str]:
        """Get current proxy configuration"""
        if not self.proxies:
            return {}
            
        # Filter out failed proxies
        available_proxies = [
            (i, proxy) for i, proxy in enumerate(self.proxies)
            if self._get_proxy_key(proxy) not in self.failed_proxies
        ]
        
        if not available_proxies:
            # Reset failed proxies if all are failed
            logger.warning("All proxies failed, resetting failure list")
            self.failed_proxies.clear()
            available_proxies = list(enumerate(self.proxies))
            
        if not available_proxies:
            return {}
            
        # Get current proxy or rotate to next
        if self.current_proxy_index >= len(available_proxies):
            self.current_proxy_index = 0
            
        _, current_proxy = available_proxies[self.current_proxy_index]
        proxy_url = self._build_proxy_url(current_proxy)
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
        
    def rotate_proxy(self):
        """Rotate to next available proxy"""
        if len(self.proxies) > 1:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            logger.info(f"Rotated to proxy {self.current_proxy_index + 1}/{len(self.proxies)}")
            
    def mark_proxy_failed(self, proxy_config: Optional[Dict] = None):
        """Mark current or specified proxy as failed"""
        if not self.proxies:
            return
            
        if proxy_config is None:
            available_proxies = [
                proxy for i, proxy in enumerate(self.proxies)
                if self._get_proxy_key(proxy) not in self.failed_proxies
            ]
            if available_proxies and self.current_proxy_index < len(available_proxies):
                proxy_config = available_proxies[self.current_proxy_index]
                
        if proxy_config:
            proxy_key = self._get_proxy_key(proxy_config)
            self.failed_proxies.add(proxy_key)
            self.proxy_stats[proxy_key]['failure_count'] += 1
            logger.warning(f"Marked proxy {proxy_key} as failed")
            
    def mark_proxy_success(self, response_time: float = 0):
        """Mark current proxy as successful"""
        if not self.proxies:
            return
            
        available_proxies = [
            proxy for proxy in self.proxies
            if self._get_proxy_key(proxy) not in self.failed_proxies
        ]
        
        if available_proxies and self.current_proxy_index < len(available_proxies):
            current_proxy = available_proxies[self.current_proxy_index]
            proxy_key = self._get_proxy_key(current_proxy)
            stats = self.proxy_stats[proxy_key]
            stats['success_count'] += 1
            stats['last_used'] = datetime.now()
            stats['response_time'].append(response_time)
            
            # Keep only last 10 response times
            if len(stats['response_time']) > 10:
                stats['response_time'] = stats['response_time'][-10:]
                
    def test_proxy(self, proxy_config: Dict, timeout: int = 10) -> Tuple[bool, float]:
        """Test individual proxy"""
        proxy_url = self._build_proxy_url(proxy_config)
        proxies = {"http": proxy_url, "https": proxy_url}
        
        try:
            start_time = time.time()
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                logger.info(f"Proxy {self._get_proxy_key(proxy_config)} working - Response time: {response_time:.2f}s")
                return True, response_time
            else:
                logger.warning(f"Proxy {self._get_proxy_key(proxy_config)} returned status {response.status_code}")
                return False, 0
                
        except Exception as e:
            logger.warning(f"Proxy {self._get_proxy_key(proxy_config)} failed: {e}")
            return False, 0
            
    def test_all_proxies(self):
        """Test all proxies and update their status"""
        logger.info("Testing all proxies...")
        self.failed_proxies.clear()
        
        for proxy_config in self.proxies:
            is_working, response_time = self.test_proxy(proxy_config)
            if not is_working:
                self.mark_proxy_failed(proxy_config)
            else:
                proxy_key = self._get_proxy_key(proxy_config)
                self.proxy_stats[proxy_key]['response_time'] = [response_time]
                
    def get_proxy_stats(self) -> Dict:
        """Get statistics for all proxies"""
        return {
            'total_proxies': len(self.proxies),
            'failed_proxies': len(self.failed_proxies),
            'current_proxy_index': self.current_proxy_index,
            'proxy_details': self.proxy_stats
        }
