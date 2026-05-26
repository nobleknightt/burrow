"""SSH tunnel management."""

import select
import socket
import threading
from types import TracebackType

import paramiko

from burrow.config import DatabaseConfig


class SSHTunnel:
    """SSH tunnel using paramiko. db-agnostic — use drivers/ to get a connection."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.client: paramiko.SSHClient | None = None
        self.transport: paramiko.Transport | None = None
        self.server_socket: socket.socket | None = None
        self.forward_threads: list[threading.Thread] = []
        self.shutdown_flag = threading.Event()
        self.local_port: int | None = None

    def _handler(self, channel: paramiko.Channel, client_socket: socket.socket) -> None:
        try:
            while not self.shutdown_flag.is_set():
                r, _, _ = select.select([channel, client_socket], [], [], 1.0)
                if channel in r:
                    data = channel.recv(1024)
                    if not data:
                        break
                    client_socket.sendall(data)
                if client_socket in r:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    channel.sendall(data)
        except Exception:
            pass
        finally:
            channel.close()
            client_socket.close()

    def _forward_tunnel(self) -> None:
        while not self.shutdown_flag.is_set():
            try:
                ready, _, _ = select.select([self.server_socket], [], [], 1.0)
                if not ready:
                    continue
                client_socket, addr = self.server_socket.accept()
                channel = self.transport.open_channel(
                    "direct-tcpip",
                    (self.config.db_host, self.config.db_port),
                    addr,
                )
                t = threading.Thread(
                    target=self._handler,
                    args=(channel, client_socket),
                    daemon=True,
                )
                t.start()
                self.forward_threads.append(t)
            except socket.timeout:
                continue
            except Exception as e:
                if not self.shutdown_flag.is_set():
                    print(f"tunnel error: {e}")
                break

    def start(self) -> None:
        if not self.config.use_ssh:
            return

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.config.ssh_host,
            port=self.config.ssh_port,
            username=self.config.ssh_user,
            key_filename=self.config.ssh_key_path,
            timeout=self.config.connection_timeout,
        )
        self.transport = self.client.get_transport()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.config.tunnel_local_port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        self.local_port = self.server_socket.getsockname()[1]

        t = threading.Thread(target=self._forward_tunnel, daemon=True)
        t.start()
        self.forward_threads.append(t)

    def stop(self) -> None:
        self.shutdown_flag.set()
        if self.server_socket:
            self.server_socket.close()
        if self.client:
            self.client.close()

    def __enter__(self) -> "SSHTunnel":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()
