"""
login.py
--------
Login handles user authentication.
"""


class Login:
    MAX_ATTEMPTS = 3

    def __init__(self, database):
        self._db = database
        self.__username = None
        self.__full_name = None
        self.__failed_attempts = 0

    @property
    def username(self):
        return self.__username

    @property
    def full_name(self):
        return self.__full_name

    @property
    def remaining_attempts(self):
        return self.MAX_ATTEMPTS - self.__failed_attempts

    def is_locked(self):
        return self.__failed_attempts >= self.MAX_ATTEMPTS

    def is_logged_in(self):
        return self.__username is not None

    def authenticate(self, username, password):
        """True if correct, False if wrong. Raises ValueError for empty input
        and PermissionError after too many wrong attempts."""
        username = username.strip()
        if not username or not password:
            raise ValueError("Please enter both username and password.")
        if self.is_locked():
            raise PermissionError("Too many failed attempts. Please restart the application.")
        full_name = self._db.verify_user(username, password)
        if full_name is None:
            self.__failed_attempts += 1
            return False
        self.__username = username.lower()
        self.__full_name = full_name
        self.__failed_attempts = 0
        return True

    def logout(self):
        self.__username = None
        self.__full_name = None
