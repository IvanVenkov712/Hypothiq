import json
from pathlib import Path

import pytest
import yaml

from config.read_config import (
    read_file_config,
    read_json_file_config,
    read_yaml_file_config,
)


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("reader", [read_yaml_file_config, read_json_file_config])
def test_readers_preserve_nested_values_and_utf8_text(tmp_path, reader, path_type):
    expected = {
        "strategy": {"name": "Стратегия", "period": 10},
        "assets": ["AAPL", "MSFT"],
        "enabled": True,
        "commission": 0.001,
        "optional": None,
    }
    if reader is read_yaml_file_config:
        content = (
            "strategy:\n  name: Стратегия\n  period: 10\n"
            "assets: [AAPL, MSFT]\nenabled: true\n"
            "commission: 0.001\noptional: null\n"
        )
    else:
        content = json.dumps(expected, ensure_ascii=False)
    path = tmp_path / "config.txt"
    path.write_text(content, encoding="utf-8")

    assert reader(path_type(path)) == expected


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("suffix, content", [
    (".yaml", "strategy: BuyAndHold\n"),
    (".yml", "strategy: BuyAndHold\n"),
    (".json", '{"strategy": "BuyAndHold"}'),
])
def test_dispatches_supported_extensions(tmp_path, suffix, content, path_type):
    path = tmp_path / f"config{suffix}"
    path.write_text(content, encoding="utf-8")

    assert read_file_config(path_type(path)) == {"strategy": "BuyAndHold"}


@pytest.mark.parametrize("filename", [
    "config", "config.txt", "config.yaml.bak",
    "config.YAML", "config.YML", "config.JSON",
])
def test_rejects_unsupported_extensions(tmp_path, filename):
    path = tmp_path / filename
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown configuration format"):
        read_file_config(path)


@pytest.mark.parametrize("reader, suffix", [
    (read_yaml_file_config, ".yaml"),
    (read_json_file_config, ".json"),
    (read_file_config, ".yaml"),
    (read_file_config, ".yml"),
    (read_file_config, ".json"),
])
def test_missing_files_raise_file_not_found(tmp_path, reader, suffix):
    with pytest.raises(FileNotFoundError):
        reader(tmp_path / f"missing{suffix}")


@pytest.mark.parametrize("reader, suffix, content, error", [
    (read_yaml_file_config, ".yaml", "strategy: [", yaml.YAMLError),
    (read_file_config, ".yaml", "strategy: [", yaml.YAMLError),
    (read_json_file_config, ".json", '{"strategy": }', json.JSONDecodeError),
    (read_file_config, ".json", '{"strategy": }', json.JSONDecodeError),
    (read_json_file_config, ".json", "", json.JSONDecodeError),
    (read_file_config, ".json", "", json.JSONDecodeError),
])
def test_invalid_documents_raise_parser_errors(tmp_path, reader, suffix, content, error):
    path = tmp_path / f"config{suffix}"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(error):
        reader(path)


@pytest.mark.parametrize("reader", [read_yaml_file_config, read_file_config])
@pytest.mark.parametrize("content", ["", "# No configuration yet\n"])
def test_empty_yaml_returns_none(tmp_path, reader, content):
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")

    assert reader(path) is None


@pytest.mark.parametrize("reader, suffix", [
    (read_yaml_file_config, ".yaml"),
    (read_json_file_config, ".json"),
    (read_file_config, ".yaml"),
    (read_file_config, ".json"),
])
@pytest.mark.parametrize("content, expected", [
    ('["AAPL", "MSFT"]', ["AAPL", "MSFT"]),
    ('"BuyAndHold"', "BuyAndHold"),
    ("42", 42),
    ("false", False),
    ("null", None),
])
def test_non_mapping_documents_are_returned_without_schema_validation(
    tmp_path, reader, suffix, content, expected,
):
    path = tmp_path / f"config{suffix}"
    path.write_text(content, encoding="utf-8")

    result = reader(path)

    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize("reader", [read_yaml_file_config, read_file_config])
def test_yaml_rejects_python_object_tags(tmp_path, reader):
    path = tmp_path / "config.yaml"
    path.write_text("!!python/tuple [1, 2]", encoding="utf-8")

    with pytest.raises(yaml.constructor.ConstructorError):
        reader(path)
