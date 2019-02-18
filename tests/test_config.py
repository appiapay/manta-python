# -*- coding: utf-8 -*-
import os
import pathlib

import pytest


@pytest.fixture
def tests_dir():
    return pathlib.Path(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture
def config_file(tests_dir):
    return open(tests_dir / 'dummyconfig.yaml')


def test_msg2config():
    from manta.messages import Destination
    import file_config

    from manta.testing import msg2config

    DestinationConfig = msg2config(Destination)

    assert file_config.utils.is_config_type(DestinationConfig)
    assert len(Destination.__attrs_attrs__) == \
        len(DestinationConfig.__attrs_attrs__)


@pytest.mark.filterwarnings("ignore:unhandled translation")
@pytest.mark.filterwarnings("ignore:field modifier")
@pytest.mark.xfail
def test_config_validation(config_file):
    import file_config

    from manta.testing.config import IntegrationConfig

    config = IntegrationConfig.load_yaml(config_file)

    assert file_config.validate(config) is None


@pytest.mark.filterwarnings("ignore:unhandled translation")
@pytest.mark.filterwarnings("ignore:field modifier")
def test_config_data_validation(config_file):
    from decimal import Decimal

    import file_config

    from manta.testing.config import IntegrationConfig

    config = IntegrationConfig.load_yaml(config_file)

    assert isinstance(config.payproc.destinations[0].amount, Decimal)


@pytest.mark.filterwarnings("ignore:unhandled translation")
def test_config2msg():
    from decimal import Decimal

    import file_config

    from manta.messages import Destination
    from manta.testing import config2msg
    from manta.testing.config import DummyPayProcConfig

    dest = Destination(
        amount=Decimal("0.01"),
        destination_address="xrb_3d1ab61eswzsgx5arwqc3gw8xjcsxd7a5egtr69jixa5it9yu9fzct9nyjyx",
        crypto_currency="NANO"
    )
    cfg_dest = DummyPayProcConfig.DestinationConfig(
        amount=Decimal("0.01"),
        destination_address="xrb_3d1ab61eswzsgx5arwqc3gw8xjcsxd7a5egtr69jixa5it9yu9fzct9nyjyx",
        crypto_currency="NANO"
    )

    assert file_config.validate(cfg_dest) is None

    converted = config2msg(cfg_dest, Destination)
    assert converted == dest


def test_config_defaults():
    from textwrap import dedent

    from file_config import config, var

    @config
    class TestConfig:
        foo = var(str, default="Default", required=False)
        bar = var(str, default="Default", required=False)

    yaml = dedent("""\
      foo: goofy
    """)

    json = dedent("""\
      {"foo": "goofy"}
    """)

    internal_cfg = TestConfig(foo="goofy")
    yaml_cfg = TestConfig.loads_yaml(yaml)
    json_cfg = TestConfig.loads_json(json)

    assert internal_cfg.foo == "goofy" and internal_cfg.bar == "Default"
    assert json_cfg.foo == "goofy" and json_cfg.bar == "Default"
    assert yaml_cfg.foo == "goofy" and yaml_cfg.bar == "Default"


def test_unique_list():
    from textwrap import dedent
    from typing import List

    import file_config
    from file_config import config, var
    import jsonschema.exceptions

    @config
    class ListCfg:

        foo = var(List[str], unique=True)

    cfg = ListCfg(foo=['a', 'b', 'c'])

    assert file_config.validate(cfg) is None

    with pytest.raises(jsonschema.exceptions.ValidationError):
        cfg = ListCfg(foo=['a', 'a', 'c'])
        assert file_config.validate(cfg) is None

    yaml = dedent("""\
      foo:
        - a
        - a
        - c
    """)

    cfg = ListCfg.loads_yaml(yaml)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        assert file_config.validate(cfg) is None
