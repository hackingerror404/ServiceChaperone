import ipaddress
import socket
import threading
import time
from urllib.parse import urlparse

from service_chaperone.models import Monitor

DEFAULT_REFERENCE_HOSTS: tuple[tuple[str, int], ...] = (
    ("1.1.1.1", 443),
    ("8.8.8.8", 443),
)

def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    cleaned = host.strip().lower()
    if cleaned == "localhost":
        return True
    try:
        return ipaddress.ip_address(cleaned).is_loopback
    except ValueError:
        return False

def is_loopback_monitor(monitor: Monitor) -> bool:
    if monitor.type == "website":
        return _is_loopback_host(urlparse(monitor.url or "").hostname)
    if monitor.type == "port":
        return _is_loopback_host(monitor.host)
    if monitor.type == "proxy":
        proxy_local = _is_loopback_host(urlparse(monitor.proxy or "").hostname)
        target_local = _is_loopback_host(urlparse(monitor.url or "").hostname)
        return proxy_local and target_local
    return False

class Connectivity:
    def __init__(
        self,
        hosts: tuple[tuple[str, int], ...] = DEFAULT_REFERENCE_HOSTS,
        timeout: float = 3.0,
        cache_ttl: float = 10.0,
    ) -> None:
        self.hosts = tuple(hosts)
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._offline_until = 0.0

    @property
    def hosts_label(self) -> str:
        return ", ".join(f"{host}:{port}" for host, port in self.hosts)

    def is_online(self) -> bool:
        now = time.monotonic()
        with self._lock:
            if now < self._offline_until:
                return False

        online = self._probe_parallel()
        with self._lock:
            if online:
                self._offline_until = 0.0
            else:
                self._offline_until = time.monotonic() + self.cache_ttl
        return online

    def _probe_parallel(self) -> bool:
        if not self.hosts:
            return True

        connected = threading.Event()
        remaining = len(self.hosts)
        done = threading.Event()
        count_lock = threading.Lock()

        def try_host(host: str, port: int) -> None:
            nonlocal remaining
            try:
                with socket.create_connection((host, port), timeout=self.timeout):
                    connected.set()
                    done.set()
                    return
            except OSError:
                pass
            finally:
                with count_lock:
                    remaining -= 1
                    if remaining == 0:
                        done.set()

        for host, port in self.hosts:
            threading.Thread(
                target=try_host, args=(host, port), daemon=True
            ).start()

        # Wait until either one host connects or all hosts have failed.
        done.wait(timeout=self.timeout + 0.5)
        return connected.is_set()