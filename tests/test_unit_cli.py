import argparse
from pathlib import Path

import pytest
from launchd_me.cli import (
    CLIArgumentParser,
    create_plist,
    install_plist,
    list_plists,
    main,
    reset_user,
    uninstall_plist,
    valid_path,
)


def test_valid_path_for_a_valid_string(tmp_path):
    """Test valid_path function with a valid string.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    """
    synthetic_script: Path = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    synthetic_script_as_string = str(synthetic_script)
    expected = valid_path(synthetic_script)
    assert expected.name == "synthetic_script.py"


def test_valid_path_returns_expected_type(tmp_path):
    """Test valid_path function returns expected type.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    """
    synthetic_script: Path = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    synthetic_script_as_string = str(synthetic_script)
    expected = valid_path(synthetic_script)
    assert isinstance(expected, Path)


def test_valid_path_for_invalid_strings():
    """Test valid_path function with invalid strings."""
    non_existent_script = "non_existent_script.py"
    with pytest.raises(argparse.ArgumentTypeError):
        valid_path(non_existent_script)


class TestCLIArgumentParser:
    """Test suite for the CLIArgumentParser class.

    This class contains tests for the CLIArgumentParser class, ensuring that the
    argument parser and its subcommands are correctly configured and function as
    expected.

    The suite assumes argparse validates values as expected. Invalid values are
    therefore not tested.
    """

    @pytest.fixture(autouse=True)
    def setup_synthetic_script_for_all_tests_in_class(self, tmp_path):
        """Setup a synthetic script for all tests in the class.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Temporary directory provided by pytest.
        """
        synthetic_script_as_a_path: Path = tmp_path / "synthetic_script.py"
        synthetic_script_as_a_path.touch()
        self.synthetic_script = str(synthetic_script_as_a_path)

    @pytest.fixture(autouse=True)
    def setup_parser_for_all_tests_in_class(self):
        """Setup the parser for all tests in the class."""
        parser_creator = CLIArgumentParser()
        self.parser = parser_creator.create_parser()

    @pytest.mark.parametrize(
        "attribute, expected_value",
        [
            ("schedule_type", "interval"),
            ("schedule_details", 300),
            ("description", "Test description"),
            ("make_executable", True),
            ("auto_install", True),
            ("func", create_plist),
        ],
    )
    def test_create_command_args(self, monkeypatch, attribute, expected_value):
        """Test the 'create' command arguments. ``script_path`` is tested separately.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        attribute : str
            The attribute to check in the parsed arguments.
        expected_value : Any
            The expected value of the attribute.
        """
        test_args = [
            "ldm",
            "create",
            self.synthetic_script,
            "interval",
            "300",
            "Test description",
        ]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert getattr(args, attribute) == expected_value

    def test_create_command_script_path_arg(self, monkeypatch):
        """Test the 'create' script path command argument.

        Separated from ``test_create_command_args`` to test against the ``.name``
        pathlib Path attribute. The full file path will change as it's a ``tmp_path``.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = [
            "ldm",
            "create",
            self.synthetic_script,
            "interval",
            "300",
            "Test description",
        ]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.script_path.name == "synthetic_script.py"

    @pytest.mark.parametrize(
        "test_args, plist_id_value",
        [(["ldm", "list"], None), (["ldm", "list", "123"], 123)],
    )
    def test_list_command_args(self, monkeypatch, test_args, plist_id_value):
        """Test the 'list' command arguments.

        ``lists_plists`` expects either no passed argument (to display all tracked
        plist files) or a ``plist_id`` to display details of a specific plist file.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        test_args : list
            The command-line arguments to test.
        plist_id_value : int or None
            The expected value of the plist_id argument.
        """
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == list_plists
        assert args.plist_id == plist_id_value

    def test_install_command_args(self, monkeypatch):
        """Test the 'install' command arguments.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "install", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == install_plist
        assert args.plist_id == "123"

    def test_uninstall_command_args(self, monkeypatch):
        """Test the 'uninstall' command arguments.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "uninstall", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == uninstall_plist
        assert args.plist_id == "123"

    def test_reset_command_args(self, monkeypatch):
        """Test the 'reset' command arguments.

        Parameters
        ----------
        monkeypatch : _pytest.monkeypatch.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "reset"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == reset_user
