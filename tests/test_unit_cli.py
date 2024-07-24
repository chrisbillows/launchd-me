import argparse
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

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
from launchd_me.plist import PlistFileIDNotFound


def test_valid_path_for_a_valid_string(tmp_path: Path):
    """Test `valid_path` function with a valid string.

    The synthetic script is passed as a string to replicate user input.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory provided by pytest.
    """
    synthetic_script = tmp_path / "synthetic_script.py"
    synthetic_script.touch()
    expected = valid_path(str(synthetic_script))
    assert expected.name == "synthetic_script.py"


def test_valid_path_returns_expected_type(tmp_path: Path):
    """Test `valid_path` function returns expected type.

    The synthetic script is passed as a string to replicate user input.

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
    """Test `valid_path` function with an invalid string."""
    non_existent_script = "non_existent_script.py"
    with pytest.raises(argparse.ArgumentTypeError):
        valid_path(non_existent_script)


class TestCLIArgumentParser:
    """Test suite for the `CLIArgumentParser` class.

    This class contains tests for the `CLIArgumentParser` class, ensuring that the
    argument parser and its subcommands are correctly configured and function as
    expected.

    The suite assumes that values are validated by argparse; invalid values are not
    tested.
    """

    @pytest.fixture(autouse=True)
    def setup_synthetic_script_for_all_tests_in_class(self, tmp_path: Path):
        """Set up a synthetic script for all tests in the class.

        Attributes
        ----------
        synthetic_script : str
            Path to a synthetic script `synthetic_script.py` in a `tmp_path`
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
            An argparse ArgumentParser configured with `launchd_me` commands and
            subcommands.
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
        """Test the `'create'` CLI command arguments.

        `script_path` is tested separately.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
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
        """Test the `'create'` script path CLI command argument.

        Separated from `test_create_command_args` to test against the `.name`
        pathlib Path attribute. The full file path changes as it's a `tmp_path`.

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
        """Test the `'list'` CLI command arguments.

        `list_plists` expects either no passed argument (to display all tracked
        plist files) or a `plist_id` to display details of a specific plist file. This
        test checks if the command line arguments for the `'uninstall'` command
        are parsed as expected using a monkeypatch to simulate command line input.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
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
        """Test the `'install'` CLI command arguments.

        This test checks if the command line arguments for the `'install'` command
        are parsed as expected using a monkeypatch to simulate command line input.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "install", "123"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == install_plist
        assert args.plist_id == "123"

    def test_uninstall_command_args(self, monkeypatch: pytest.MonkeyPatch):
        """Test the `'uninstall'` CLI command arguments.

        This test checks if the command line arguments for the `'uninstall'` command
        are parsed as expected using a monkeypatch to simulate command line input.

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
        """Test the `'reset'` CLI command arguments.

        This test checks if the command line arguments for the `'reset'` command
        are parsed as expected using a monkeypatch to simulate command line input.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Monkeypatch fixture to modify sys.argv.
        """
        test_args = ["ldm", "reset"]
        monkeypatch.setattr("sys.argv", test_args)
        args = self.parser.parse_args()
        assert args.func == reset_user


@patch("launchd_me.cli.PlistCreator")
def test_create_plist(MockPlistCreator: Mock):
    """Test the `create_plist` function within the CLI.

    Test `create_plist` calls the expected methods with the expected values, based
    on the passed arguments. Mocks are used to simulate the creator process, validating
    that the function's flow and data handling are as expected.
    """
    args = argparse.Namespace(
        script_path="path/to/script",
        schedule_type="interval",
        schedule_details={"interval": 300},
        description="Test script",
        make_executable=True,
        auto_install=True,
    )
    mock_plist_creator = MockPlistCreator.return_value
    mock_plist_creator.driver.return_value = Path("plist_file_path")
    create_plist(args)
    mock_plist_creator.driver.assert_called_once()


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

    @patch("launchd_me.cli.DbDisplayer")
    @patch("launchd_me.cli.PlistDbGetters")
    def test_list_plists_without_id_arg(
        self, MockDbGetters: Mock, MockDbDisplayer: Mock
    ):
        """Test `list_plists` for its ability to list all tracked plist files.

        This method asserts that if no plist ID is provided in the arguments,
        `list_plists` retrieves all tracked plist files and then correctly passes the
        response to the display function.

        Mocks are used to simulate the retrieval and display processes, validating that
        the function's flow and data handling are as expected.

        Parameters
        ----------
        MockDbGetters : Mock
            A mock of the PlistDbGetters class to simulate database interactions.
        MockDbDisplayer : Mock
            A mock of the DbDisplayer class to simulate the display functionality.
        """
        args = argparse.Namespace(plist_id=None)

        mock_db_getter = MockDbGetters.return_value
        mock_db_displayer = MockDbDisplayer.return_value
        mock_db_getter.get_all_tracked_plist_files.return_value = [
            {"id": "123", "name": "TestPlist"}
        ]
        list_plists(args)
        mock_db_getter.get_all_tracked_plist_files.assert_called_once()
        mock_db_displayer.display_all_tracked_plist_files_table.assert_called_once_with(
            [{"id": "123", "name": "TestPlist"}]
        )

    @patch("launchd_me.cli.DbDisplayer")
    @patch("launchd_me.cli.PlistDbGetters")
    def test_list_plists_with_id_arg(self, MockDbGetters: Mock, MockDbDisplayer: Mock):
        """Test `list_plists` for its behaviour when a specific plist ID is provided.

        This method asserts that providing a plist ID causes `list_plists` to retrieve
        details for the given plist ID and pass the response to the display function.

        Mocks are used to simulate the retrieval and display processes, validating that
        the function's flow and data handling are as designed.

        Parameters
        ----------
        MockDbGetters : Mock
            A mock of the PlistDbGetters class to simulate database interactions.
        MockDbDisplayer : Mock
            A mock of the DbDisplayer class to simulate the display functionality.
        """
        args = argparse.Namespace(plist_id="123")
        mock_db_getters = MockDbGetters.return_value
        mock_db_displayer = MockDbDisplayer.return_value
        mock_db_getters.get_a_single_plist_file_details.return_value = {
            "id": "123",
            "name": "TestPlist",
        }
        list_plists(args)
        mock_db_getters.get_a_single_plist_file_details.assert_called_once_with("123")
        mock_db_displayer.display_single_plist_file_detail_table.assert_called_once_with(
            {"id": "123", "name": "TestPlist"}
        )


@patch("launchd_me.cli.USER_CONFIG", autospec=True)
@patch("launchd_me.cli.PlistDbGetters")
@patch("launchd_me.cli.PlistDbSetters")
@patch("launchd_me.cli.PlistInstallationManager")
def test_install_plist(
    MockInstallationManager: Mock,
    MockDbSetters: Mock,
    MockDbGetters: Mock,
    MockUserConfig: Mock,
):
    """Test the `install_plist` function within the CLI.

    Test `install_plist` calls the expected methods with the expected values, based
    on the passed arguments. Mocks are used to simulate the getter, setter and install
    processes, validating that the function's flow and data handling are as expected.
    """
    args = argparse.Namespace(plist_id="123")

    mock_db_getter = MockDbGetters.return_value
    mock_db_setter = MockDbSetters.return_value
    mock_installation_manager = MockInstallationManager.return_value
    mock_user_config = MockUserConfig.return_value

    mock_db_getter.verify_a_plist_id_is_valid.return_value = None
    mock_db_getter.get_a_single_plist_file_details.return_value = {
        "plist_id": "123",
        "PlistFileName": "synthetic_file_name",
    }
    mock_installation_manager.install_plist.return_value
    mock_user_config.plist_dir = "a_directory"

    install_plist(args)

    mock_db_getter.verify_a_plist_id_is_valid.assert_called_once_with("123")
    mock_db_getter.get_a_single_plist_file_details.assert_called_once_with("123")
    mock_installation_manager.install_plist.assert_called_once_with(
        "123", Path("synthetic_file_name")
    )


@patch("launchd_me.cli.USER_CONFIG", autospec=True)
@patch("launchd_me.cli.PlistDbGetters")
@patch("launchd_me.cli.PlistDbSetters")
@patch("launchd_me.cli.PlistInstallationManager")
def test_uninstall_plist(
    MockInstallationManager, MockDbSetters, MockDbGetters, MockUserConfig
):
    """Assert that the expected methods are called with the expected values, based on
    the passed arguments.
    """
    args = argparse.Namespace(plist_id="123")

    mock_db_getter = MockDbGetters.return_value
    mock_db_setter = MockDbSetters.return_value
    mock_installation_manager = MockInstallationManager.return_value
    mock_user_config = MockUserConfig.return_value

    mock_db_getter.verify_a_plist_id_is_valid.return_value = None
    mock_db_getter.get_a_single_plist_file_details.return_value = {
        "plist_id": "123",
        "PlistFileName": "synthetic_file_name",
    }
    mock_installation_manager.uninstall_plist.return_value
    mock_user_config.launch_agents_dir = "a_directory"

    uninstall_plist(args)

    mock_db_getter.verify_a_plist_id_is_valid.assert_called_once_with("123")
    mock_db_getter.get_a_single_plist_file_details.assert_called_once_with("123")
    mock_installation_manager.uninstall_plist.assert_called_once_with(
        "123", Path("synthetic_file_name")
    )


# TODO: Wait until the functionality is finished.
def test_reset_user():
    args = argparse.Namespace()
    pass


@patch("launchd_me.cli.CLIArgumentParser")
@patch("launchd_me.cli.LaunchdMeInit")
def test_entry_point_main_passes_for_valid_args(
    MockLaunchdMeInit: Mock, MockCLIArgumentParser: Mock
):
    """Test the `main` entry point for launchd_me.

    Tests `main` initializes the required components and executes the function
    specified in the command-line arguments (via the subparsers `func` properties).

    `mock_parser` represents the Argparse.ArgumentParser created by
    `CLIArgumentParser.create_parser()`. Mock function represents a CLI command
    function (e.g. `create_plist`).
    """
    mock_launchd_me_init = MockLaunchdMeInit.return_value
    mock_cli_argument_parser = MockCLIArgumentParser.return_value
    mock_parser = Mock()
    mock_function = Mock()

    mock_parser.parse_args.return_value = argparse.Namespace(func=mock_function)
    mock_launchd_me_init.initialise_launchd_me.return_value = None
    mock_cli_argument_parser.create_parser.return_value = mock_parser

    main()

    mock_launchd_me_init.initialise_launchd_me.assert_called_once_with()
    mock_cli_argument_parser.create_parser.assert_called_once_with()
    mock_function.assert_called_once()


@patch("launchd_me.cli.CLIArgumentParser")
@patch("launchd_me.cli.LaunchdMeInit")
def test_main_entry_point_handles_exceptions(
    MockLaunchdMeInit: Mock, MockCLIArgumentParser: Mock
):
    """Test the `main` entry point for launchd_me handles propagated Exceptions.

    Mocks the required components and executes the function specified in the
    command-line arguments (via the subparsers `func` properties).

    The function `mock_function` replicates producing a `PlistFileIDNotFound` error.
    The test checks `main` handles this exception by printing the appropriate error
    message.

    - `mock_parser` represents the Argparse.ArgumentParser created by
      `CLIArgumentParser.create_parser()`.
    - `mock_function` represents a CLI command function that returns a
      `PlistFileIDNotFound` error (e.g. `list_plist`).
    - `mock_print` captures what `main` attempts to print.

    The test first asserts `mock_print` was called once. The test captures the `args`
    passed to `mocked_print` and casts the result to a string as `actual`. The test
    casts `synthetic_exception` to a string as `expected`.

    `print` automatically casts an exceptions to strings so equality between strings
    correctly represents the function's true output.

    Note
    ----
    Exceptions aren't equal i.e. `PlistFileIDNotFound("message")` !=
    `PlistFileIDNotFound("message")` - which would have been a simpler, but less
    accurate, test.
    """
    # Create mocks for the test.
    mock_launchd_me_init = MockLaunchdMeInit.return_value
    mock_cli_argument_parser = MockCLIArgumentParser.return_value
    mock_parser = Mock()

    # Configure the mock function to simulate raising an error when called.
    synthetic_exception = PlistFileIDNotFound("There is no plist file with the ID: 2")
    mock_function = Mock(side_effect=synthetic_exception)

    # Configure returns values for the mocked parser's parse_args method and other
    # initialization steps.
    mock_parser.parse_args.return_value = argparse.Namespace(func=mock_function)
    mock_launchd_me_init.initialise_launchd_me.return_value = None
    mock_cli_argument_parser.create_parser.return_value = mock_parser

    # Patch the built-in print function to monitor its usage and capture the arguments
    # it receives.
    with patch("builtins.print") as mock_print:
        main()

    # First assertion.
    mock_print.assert_called_once()

    # For comparison, convert the synthetic exception to a string.
    expected = str(synthetic_exception)

    # Retrieve the actual argument passed to the mocked print function.
    args, kwargs = mock_print.call_args
    # For comparison, convert the actual printed argument to a string.
    actual = str(args[0])
    assert actual == expected
