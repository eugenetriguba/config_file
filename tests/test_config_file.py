import json
from pathlib import Path

import pytest

from config_file.config_file import ConfigFile
from config_file.exceptions import MissingKeyError
from config_file.parsers.abstract_parser import AbstractParser

SUPPORTED_FILE_TYPES = ["ini", "json", "yaml", "toml"]


@pytest.fixture(params=SUPPORTED_FILE_TYPES)
def template_and_config_file(request, template_file):
    def func(template_name: str = "default", parser: AbstractParser = None):
        template = template_file(request.param, template_name)
        return template, ConfigFile(template, parser=parser)

    return func


@pytest.fixture(params=SUPPORTED_FILE_TYPES)
def templated_config_file(template_and_config_file):
    def func(template_name: str = "default", parser: AbstractParser = None):
        return template_and_config_file(template_name, parser)[1]

    return func


def test_that_config_file_is_initialized_correctly(template_and_config_file):
    template_file, config = template_and_config_file()

    assert config.file_path == template_file
    assert config.stringify() == template_file.read_text()
    assert isinstance(config._ConfigFile__parser, AbstractParser)


def test_that_a_tidle_in_the_config_path_expands_to_the_absolute_path():
    config_name = "temp.ini"
    config_path = "~/" + config_name

    try:
        Path(config_path).expanduser().touch()
        assert ConfigFile(config_path).file_path == Path.home() / config_name
    finally:
        Path(config_path).expanduser().unlink()


@pytest.mark.skip(msg="needs fixing up")
@pytest.mark.parametrize("path", ["", "invalid", "invalid.conf"])
def test_invalid_path_raises_value_error(path):
    with pytest.raises(ValueError):
        ConfigFile(path)


def test_that_config_file_can_save(template_and_config_file):
    template_file, config = template_and_config_file()

    config.set("header_one.number_key", 25)
    config.save()

    assert config.stringify() == template_file.read_text()


def test_that_config_file_can_restore_the_original(
    templated_config_file, template_original_file
):
    config = templated_config_file()
    original_file = template_original_file(config.file_path)

    config.set("header_one.number_key", 5)
    config.restore_original()

    assert config.stringify() == original_file.read_text()


def test_missing_config_file_during_restore(templated_config_file):
    config = templated_config_file()

    with pytest.raises(FileNotFoundError) as error:
        config.restore_original()

    assert "The specified config file" in str(error)
    assert "does not exist" in str(error)


@pytest.mark.parametrize(
    "key, expected_result",
    [
        ("header_one", True),
        ("header_one.number_key", True),
        ("header_one.blah", False),
    ],
)
def test_that_config_file_can_find_sections_and_keys(
    templated_config_file, key, expected_result
):
    config = templated_config_file()
    assert config.has(key) == expected_result


@pytest.mark.parametrize(
    "section_key, value, parse_type, return_type, default, file_name, file_contents",
    [
        (
            "calendar.sunday_index",
            0,
            True,
            None,
            False,
            "config.ini",
            "[calendar]\nsunday_index = 0\n\n",
        ),
        (
            "calendar.sunday_index",
            "0",
            False,
            None,
            False,
            "config.ini",
            "[calendar]\nsunday_index = 0\n\n",
        ),
        (
            "calendar.sunday_index",
            0,
            False,
            None,
            False,
            "config.json",
            json.dumps({"calendar": {"sunday_index": 0}}),
        ),
        (
            "calendar.missing",
            "my default value",
            False,
            None,
            "my default value",
            "config.json",
            json.dumps({"calendar": 5}),
        ),
        (
            "calendar.sunday_index",
            0,
            False,
            int,
            False,
            "config.ini",
            "[calendar]\nsunday_index = 0\n\n",
        ),
    ],
)
def test_that_config_file_can_get(
    tmpdir,
    section_key,
    value,
    return_type,
    parse_type,
    file_name,
    file_contents,
    default,
):
    config_path = tmpdir / file_name
    config_path.write_text(file_contents, encoding="utf-8")
    config = ConfigFile(config_path)

    ret_val = config.get(section_key, parse_types=parse_type, default=default)
    if return_type is not None:
        assert return_type(ret_val) == value
    else:
        assert ret_val == value


@pytest.mark.parametrize("key", ["header_one.number_key", "header_one"])
def test_that_config_file_can_delete(templated_config_file, key):
    config = templated_config_file()

    config.delete(key)

    assert config.has(key) is False


@pytest.mark.parametrize("key", ["", 0, False, {}, "header_one.does_not_exist"])
def test_that_config_file_raises_missing_key_error_on_invalid_input_or_missing_key(
    templated_config_file, key
):
    config = templated_config_file()

    with pytest.raises(MissingKeyError):
        config.delete(key)
