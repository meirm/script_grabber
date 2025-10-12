"""Unit tests for ScriptGrabber exception hierarchy."""

import pytest
from script_grabber.grabexceptions import (
    GrabError,
    GrabTimeoutError,
    GrabConnectionError,
    GrabNetworkError,
    GrabMisuseError,
    GrabConfigError,
    GrabLockError,
)


@pytest.mark.unit
class TestExceptionInstantiation:
    """Test that all exception classes can be instantiated with proper messages."""

    def test_grab_error_instantiation(self):
        """Test GrabError can be instantiated with a message."""
        error = GrabError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"

    def test_grab_timeout_error_instantiation(self):
        """Test GrabTimeoutError can be instantiated with a message."""
        error = GrabTimeoutError("Operation timed out")
        assert str(error) == "Operation timed out"
        assert error.message == "Operation timed out"

    def test_grab_connection_error_instantiation(self):
        """Test GrabConnectionError can be instantiated with a message."""
        error = GrabConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.message == "Connection failed"

    def test_grab_network_error_instantiation(self):
        """Test GrabNetworkError can be instantiated with a message."""
        error = GrabNetworkError("Network unreachable")
        assert str(error) == "Network unreachable"
        assert error.message == "Network unreachable"

    def test_grab_misuse_error_instantiation(self):
        """Test GrabMisuseError can be instantiated with a message."""
        error = GrabMisuseError("Invalid usage")
        assert str(error) == "Invalid usage"
        assert error.message == "Invalid usage"

    def test_grab_config_error_instantiation(self):
        """Test GrabConfigError can be instantiated with a message."""
        error = GrabConfigError("Configuration invalid")
        assert str(error) == "Configuration invalid"
        assert error.message == "Configuration invalid"

    def test_grab_lock_error_instantiation(self):
        """Test GrabLockError can be instantiated with a message."""
        error = GrabLockError("Lock file exists")
        assert str(error) == "Lock file exists"
        assert error.message == "Lock file exists"


@pytest.mark.unit
class TestExceptionInheritance:
    """Test inheritance chain: GrabError → specific exceptions."""

    def test_grab_timeout_error_inheritance(self):
        """Test GrabTimeoutError inherits from GrabError."""
        error = GrabTimeoutError("Timeout")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)

    def test_grab_connection_error_inheritance(self):
        """Test GrabConnectionError inherits from GrabError."""
        error = GrabConnectionError("Connection issue")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)

    def test_grab_network_error_inheritance(self):
        """Test GrabNetworkError inherits from GrabError."""
        error = GrabNetworkError("Network issue")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)

    def test_grab_misuse_error_inheritance(self):
        """Test GrabMisuseError inherits from GrabError."""
        error = GrabMisuseError("Misuse")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)

    def test_grab_config_error_inheritance(self):
        """Test GrabConfigError inherits from GrabError."""
        error = GrabConfigError("Config issue")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)

    def test_grab_lock_error_inheritance(self):
        """Test GrabLockError inherits from GrabError."""
        error = GrabLockError("Lock issue")
        assert isinstance(error, GrabError)
        assert isinstance(error, Exception)


@pytest.mark.unit
class TestExceptionCatching:
    """Test that exceptions can be caught by base class."""

    def test_catch_timeout_error_as_grab_error(self):
        """Test GrabTimeoutError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabTimeoutError("Timeout occurred")

    def test_catch_connection_error_as_grab_error(self):
        """Test GrabConnectionError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabConnectionError("Connection lost")

    def test_catch_network_error_as_grab_error(self):
        """Test GrabNetworkError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabNetworkError("Network down")

    def test_catch_misuse_error_as_grab_error(self):
        """Test GrabMisuseError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabMisuseError("Invalid call")

    def test_catch_config_error_as_grab_error(self):
        """Test GrabConfigError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabConfigError("Bad config")

    def test_catch_lock_error_as_grab_error(self):
        """Test GrabLockError can be caught as GrabError."""
        with pytest.raises(GrabError):
            raise GrabLockError("Lock conflict")

    def test_catch_all_grab_errors(self):
        """Test all GrabError subclasses can be caught with single handler."""
        errors = [
            GrabTimeoutError("timeout"),
            GrabConnectionError("connection"),
            GrabNetworkError("network"),
            GrabMisuseError("misuse"),
            GrabConfigError("config"),
            GrabLockError("lock"),
        ]

        for error in errors:
            with pytest.raises(GrabError):
                raise error


@pytest.mark.unit
class TestExceptionMessages:
    """Test that exception messages are preserved correctly."""

    def test_exception_message_preservation(self):
        """Test that exception messages are accessible and preserved."""
        test_message = "This is a detailed error message"
        error = GrabError(test_message)

        assert error.message == test_message
        assert str(error) == test_message

    def test_exception_message_with_formatting(self):
        """Test exception messages with string formatting."""
        grabber_name = "test_grabber"
        path = "/path/to/lock"
        message = f"Grabber {grabber_name} lock at {path}"

        error = GrabLockError(message)
        assert grabber_name in str(error)
        assert path in str(error)

    def test_empty_message(self):
        """Test exception with empty message."""
        error = GrabError("")
        assert str(error) == ""
        assert error.message == ""

    def test_multiline_message(self):
        """Test exception with multiline message."""
        message = "Line 1\nLine 2\nLine 3"
        error = GrabError(message)
        assert str(error) == message
        assert "\n" in str(error)
