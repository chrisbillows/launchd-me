import argparse
from pathlib import Path

import pytest
from launchd_me.cli import (
    create_plist,
    get_args,
    install_plist,
    list_plists,
    main,
    reset_user,
    uninstall_plist,
    valid_path,
)


def test_valid_path_for_a_valid_string(tmp_path):
    synthetic_script: Path = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    synthetic_script_as_string = str(synthetic_script)
    expected = valid_path(synthetic_script)
    assert expected.name == "synthetic_script.py"


def test_valid_path_returns_expected_type(tmp_path):
    synthetic_script: Path = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    synthetic_script_as_string = str(synthetic_script)
    expected = valid_path(synthetic_script)
    assert isinstance(expected, Path)


def test_valid_path_for_invalid_strings():
    non_existent_script = "non_existent_script.py"
    with pytest.raises(argparse.ArgumentTypeError):
        valid_path(non_existent_script)


class TestGetArgs:
    @pytest.fixture(autouse=True)
    def setup_for_all_tests_in_class(self, tmp_path):
        synthetic_script_as_a_path: Path = tmp_path / "synthetic_script.py"
        synthetic_script_as_a_path.touch()
        self.synthetic_script = str(synthetic_script_as_a_path)

    @pytest.mark.parametrize(
        "attribute, expected_value",
        [
            ("command", "create"),
            ("schedule_type", "interval"),
            ("schedule_details", 300),
            ("description", "Test description"),
            ("make_executable", True),
            ("auto_install", True),
        ],
    )
    def test_get_args_create_command(self, monkeypatch, attribute, expected_value):
        test_args = [
            "ldm",
            "create",
            self.synthetic_script,
            "interval",
            "300",
            "Test description",
        ]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert getattr(args, attribute) == expected_value

    def test_get_args_create_command_for_script_path(self, monkeypatch):
        test_args = [
            "ldm",
            "create",
            self.synthetic_script,
            "interval",
            "300",
            "Test description",
        ]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert args.script_path.name == "synthetic_script.py"

    def test_get_args_list_command(self, monkeypatch):
        test_args = ["ldm", "list", "-p", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert args.command == "list"
        assert args.plist_id == 123

    def test_get_args_install_command(self, monkeypatch):
        test_args = ["ldm", "install", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert args.command == "install"
        assert args.plist_id == "123"

    def test_get_args_uninstall_command(self, monkeypatch):
        test_args = ["ldm", "uninstall", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert args.command == "uninstall"
        assert args.plist_id == "123"

    def test_get_args_reset_command(self, monkeypatch):
        test_args = ["ldm", "reset"]
        monkeypatch.setattr("sys.argv", test_args)
        args = get_args()
        assert args.command == "reset"
