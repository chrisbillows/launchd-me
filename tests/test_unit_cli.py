import argparse
from pathlib import Path
from typing import Any
from unittest.mock import patch

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
from launchd_me.plist import DbDisplayer


def test_valid_path_for_a_valid_string(tmp_path: Path):
    """Test ``valid_path`` function with a valid string.

    The script is passed as a string to replicate user input.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory provided by pytest.
    """
    synthetic_script = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    expected = valid_path(str(synthetic_script))
    assert expected.name == "synthetic_script.py"


def test_valid_path_returns_expected_type(tmp_path: Path):
    """Test ``valid_path`` function returns expected type.

    The script is passed as a string to replicate user input.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    """
    synthetic_script: Path = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    expected = valid_path(str(synthetic_script))
    assert isinstance(expected, Path)


def test_valid_path_for_invalid_strings():
    """Test ``valid_path`` function with invalid strings."""
    non_existent_script = "non_existent_script.py"
    with pytest.raises(argparse.ArgumentTypeError):
        valid_path(non_existent_script)


class TestCLIArgumentParser:
    """Test suite for the ``CLIArgumentParser`` class.

    This class contains tests for the ``CLIArgumentParser`` class, ensuring that the
    argument parser and its subcommands are correctly configured and function as
    expected.

    The suite assumes values are validated by argparse. Invalid values are not tested.
    """

    @pytest.fixture(autouse=True)
    def setup_synthetic_script_for_all_tests_in_class(self, tmp_path: Path):
        """Set up a synthetic script for all tests in the class.

        Attributes
        ----------
        synthetic_script : str
            Path to a synthetic script "synthetic_script.py" in a ``tmp_path``
            directory.

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
        """Setup a Parser for all tests in the class.

        Attributes
        ----------
        Argparse.ArgumentParser
            Configured with commands and subcommands.
        """
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
    def test_create_command_args(
        self, monkeypatch: pytest.MonkeyPatch, attribute: str, expected_value: Any
    ):
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

    def test_create_command_script_path_arg(self, monkeypatch: pytest.MonkeyPatch):
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
    def test_list_command_args(
        self, monkeypatch: pytest.MonkeyPatch, test_args: list, plist_id_value: Any
    ):
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

    def test_install_command_args(self, monkeypatch: pytest.MonkeyPatch):
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

    def test_uninstall_command_args(self, monkeypatch: pytest.MonkeyPatch):
        """Test the 'uninstall' command arguments.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "uninstall", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == uninstall_plist
        assert args.plist_id == "123"

    def test_reset_command_args(self, monkeypatch: pytest.MonkeyPatch):
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


class TestListPlists:
    """A test suite for testing the `list_plists` function within the CLI.

    This class contains tests that verify whether `list_plists` handles the
    display of plist files correctly, based on different conditions provided
    through command-line arguments.

    Methods
    -------
    test_list_plists_without_id()
        Test the behaviour of `list_plists` when no specific plist ID is provided.
    test_list_plists_with_id()
        Test the behaviour of `list_plists` when a specific plist ID is provided.
    """

    def test_list_plists_without_id(self):
        """Test `list_plists` for its ability to list all tracked plist files.

        This method asserts that if no plist ID is provided in the arguments,
        `list_plists` retrieves all tracked plist files and then correctly passes the
        response to the display function.

        Mocks are used to simulate the retrieval and display processes, validating that
        the function's flow and data handling are as designed.
        """
        args = argparse.Namespace(plist_id=None)
        with patch("launchd_me.cli.PlistDbGetters") as MockDbGetter, patch(
            "launchd_me.cli.DbDisplayer"
        ) as MockDbDisplayer:
            mock_db_getter = MockDbGetter.return_value
            mock_db_displayer = MockDbDisplayer.return_value
            mock_db_getter.get_all_tracked_plist_files.return_value = [
                {"id": "123", "name": "TestPlist"}
            ]
            list_plists(args)
            mock_db_getter.get_all_tracked_plist_files.assert_called_once()
            mock_db_displayer.display_all_tracked_plist_files_table.assert_called_once_with(
                [{"id": "123", "name": "TestPlist"}]
            )

    def test_list_plists_with_id(self):
        """Test `list_plists` for its behaviour when a specific plist ID is provided.

        This method asserts that providing a plist ID causes `list_plists` to retrieve
        details for the given plist ID and pass the response to the display function.

        Mocks are used to simulate the retrieval and display processes, validating that
        the function's flow and data handling are as designed.
        """
        args = argparse.Namespace(plist_id="123")
        with patch("launchd_me.cli.PlistDbGetters") as MockDbGetter, patch(
            "launchd_me.cli.DbDisplayer"
        ) as MockDbDisplayer:
            mock_db_getter = MockDbGetter.return_value
            mock_db_displayer = MockDbDisplayer.return_value
            mock_db_getter.get_a_single_plist_file_details.return_value = {
                "id": "123",
                "name": "TestPlist",
            }
            list_plists(args)
            mock_db_getter.get_a_single_plist_file_details.assert_called_once_with(
                "123"
            )
            mock_db_displayer.display_single_plist_file_detail_table.assert_called_once_with(
                {"id": "123", "name": "TestPlist"}
            )
