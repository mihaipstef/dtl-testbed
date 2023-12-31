import os
import pytest
from testbed import (
    db,
    ns,
)
from uuid import uuid4


@pytest.fixture
def _env_db_cfg():
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    return {
        "db_type": "mongo",
        "access": {
            "uri": f"mongodb://probe:probe@{db_host}:27017/monitor?authSource=admin"
        },
    }


@pytest.fixture
def _env_tun_cfg(_env_db_cfg):
    return {
        "monitor_db": _env_db_cfg,
        "monitor_probe": "tcp://127.0.0.1:5555",
        "type": "sim",
        "mode": "tun",
        "tunnel": [("2.2.2.2",), ("3.3.3.3",)]
    }


@pytest.fixture
def _env_tap_cfg(_env_db_cfg):
    return {
        "monitor_db": _env_db_cfg,
        "monitor_probe": "tcp://127.0.0.1:5555",
        "type": "sim",
        "mode": "tap",
        "tunnel": [("2.2.2.2",), ("3.3.3.3",)]
    }


@pytest.fixture
def tun_env(_env_tun_cfg):
    env_name = "pytest0"
    # create the network environment
    env = ns.create_tun_env(env_name, _env_tun_cfg, overwrite=True)
    # pass environment information to the test
    yield {
        "env_cfg": _env_tun_cfg,
        "env": env,
        "name": env.netns,
    }
    # cleanup the network env
    ns.delete_env(env_name)


@pytest.fixture
def tap_env(_env_tap_cfg):
    env_name = "pytest1"
    # create the network environment
    env = ns.create_tap_env(env_name, _env_tap_cfg, overwrite=True)
    # pass environment information to the test
    yield {
        "env_cfg": _env_tap_cfg,
        "env": env,
        "name": env.netns,
    }
    # cleanup the network env
    ns.delete_env(env_name)
