import socket

from somabrain import ports


def test_pick_free_port_skips_bound_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    bound_port = sock.getsockname()[1]
    try:
        next_port = ports.pick_free_port(bound_port, attempts=10)
        assert next_port != bound_port
        assert ports.is_port_free(next_port)
    finally:
        sock.close()


def test_allocate_ports_returns_expected_keys():
    allocation = ports.allocate_ports({"TEST_PORT": 45000})
    assert set(allocation.keys()) == {"TEST_PORT"}
    assert ports.is_port_free(allocation["TEST_PORT"])  # should still be free
