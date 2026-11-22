"""
main.py - run this file to start the application:  python main.py
"""
from database import Database
from inventory import Inventory
from sales import Sales
from login import Login
from gui import LoginWindow, DrugManagementSystem


def make_sharp_on_windows():
    """Stops Windows from blurring the window when display scaling is 125% / 150%."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass            # not Windows (or very old Windows): nothing to do


def run():
    make_sharp_on_windows()      # must run before any window is created
    database = Database()
    inventory = Inventory(database)
    sales = Sales(database, inventory)
    login = Login(database)

    while True:
        login.logout()
        login_window = LoginWindow(login)
        login_window.mainloop()
        if not login.is_logged_in():      # window closed or locked out
            break
        app = DrugManagementSystem(inventory, sales, login)
        app.mainloop()
        if not app.logged_out:            # window closed with the X button
            break
    database.close()


if __name__ == "__main__":
    run()
