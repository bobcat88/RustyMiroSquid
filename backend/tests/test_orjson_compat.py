import pytest
import orjson
import datetime

def test_orjson_dump_load():
    # test compatibility with OPT_NON_STR_KEYS
    data = {1: "one", "two": 2}
    dumped = orjson.dumps(data, option=orjson.OPT_NON_STR_KEYS)
    assert dumped is not None
    loaded = orjson.loads(dumped)
    assert loaded["1"] == "one" # orjson stringifies integer keys
    assert loaded["two"] == 2

def test_orjson_error():
    with pytest.raises(orjson.JSONDecodeError):
        orjson.loads(b"invalid json")
