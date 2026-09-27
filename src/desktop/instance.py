import hashlib
import time
from PySide6.QtCore import QObject, Signal, Slot, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class InstanceGuard(QObject):
    open_requested = Signal()

    def __init__(self, data_dir):
        super().__init__()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(data_dir / "instance.lock"))
        self.lock.setStaleLockTime(0)
        self.name = (
            "tikoplay-"
            + hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()[:24]
        )
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self._connected)
        self.owner = False

    def acquire_or_notify(self):
        if self.lock.tryLock(0):
            self.owner = True
            QLocalServer.removeServer(self.name)
            if not self.server.listen(self.name):
                self.close()
                raise RuntimeError("Nie można uruchomić lokalnego kanału TikoPlay.")
            return True
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            sock = QLocalSocket()
            sock.connectToServer(self.name)
            if sock.waitForConnected(200):
                sock.write(b"OPEN_PANEL\n")
                sock.waitForBytesWritten(500)
                sock.disconnectFromServer()
                return False
            time.sleep(0.05)
        raise RuntimeError(
            "TikoPlay już działa, ale nie odpowiada. Zakończ istniejącą instancję i spróbuj ponownie."
        )

    def _connected(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            sock.setProperty("buffer", b"")
            sock.readyRead.connect(self._socket_ready)
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():
                self._read(sock)

    @Slot()
    def _socket_ready(self):
        self._read(self.sender())

    def _read(self, sock):
        data = sock.property("buffer") + bytes(sock.readAll())
        if len(data) > 64:
            sock.abort()
            return
        sock.setProperty("buffer", data)
        if b"\n" in data:
            if data == b"OPEN_PANEL\n":
                self.open_requested.emit()
                sock.write(b"ACK\n")
                sock.flush()
            sock.disconnectFromServer()

    def close(self):
        if self.owner:
            self.server.close()
            self.lock.unlock()
            self.owner = False
