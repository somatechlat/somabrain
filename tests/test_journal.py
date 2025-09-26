from somabrain import journal


def test_append_and_iterate_journal(tmp_path):
    base = str(tmp_path)
    ns = "testns"
    ev1 = {"type": "mem", "key": "k1", "value": "v1"}
    ev2 = {"type": "mem", "key": "k2", "value": "v2"}

    journal.append_event(base, ns, ev1)
    journal.append_event(base, ns, ev2)

    items = list(journal.iter_events(base, ns))
    assert any(i.get("key") == "k1" for i in items)
    assert any(i.get("key") == "k2" for i in items)


def test_rotate_and_compact(tmp_path):
    base = str(tmp_path)
    ns = "rot"
    # write several events
    for i in range(10):
        journal.append_event(base, ns, {"type": "mem", "key": f"k{i}", "value": i})
    # rotate with tiny max_bytes
    rot = journal.rotate_journal(base, ns, max_bytes=1, keep=2)
    assert rot is not None
    # compact should succeed
    ok = journal.compact_journal(base, ns)
    assert ok
