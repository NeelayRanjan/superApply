import socket

import pytest


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    original = socket.socket.connect

    def guarded(sock, address):
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"Tests must not use external network: {address}")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


@pytest.fixture
def db():
    from firstlook.db import connect

    connection = connect(":memory:")
    yield connection
    connection.close()
