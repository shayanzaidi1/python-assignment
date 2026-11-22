"""
database.py
-----------
Handles every SQLite operation.  The rest of the program never writes SQL;
it only calls the simple methods below (ABSTRACTION), and the connection is
stored in a private attribute (ENCAPSULATION).
All queries are parameterized (the ? marks) to prevent SQL injection.
"""
import hashlib
import hmac
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharmacy.db")


class BaseManager(ABC):
    """Abstract parent of Inventory and Sales (inheritance + abstraction)."""

    def __init__(self, database):
        self._db = database

    @abstractmethod
    def summary(self):
        """Each manager describes itself differently (polymorphism)."""


class Database:
    def __init__(self, db_file=DB_FILE):
        self.__conn = sqlite3.connect(db_file)
        self.__conn.row_factory = sqlite3.Row
        self.__create_tables()
        self.__add_sample_data()

    # ------------------------------------------------------------ private
    def __create_tables(self):
        self.__conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                username      TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                full_name     TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drugs (
                drug_id      TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                category     TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                price        REAL NOT NULL,
                quantity     INTEGER NOT NULL CHECK (quantity >= 0),
                expiry_date  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sales (
                sale_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_id     TEXT NOT NULL,
                drug_name   TEXT NOT NULL,
                quantity    INTEGER NOT NULL,
                unit_price  REAL NOT NULL,
                total_price REAL NOT NULL,
                sale_date   TEXT NOT NULL,
                sold_by     TEXT NOT NULL
            );
            """
        )

    @staticmethod
    def __hash(password, salt):
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def __add_user(self, username, password, full_name):
        salt = os.urandom(8).hex()
        self.__conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            (username, self.__hash(password, salt), salt, full_name),
        )

    def __add_sample_data(self):
        with self.__conn:
            if self.__conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                self.__add_user("admin", "admin123", "Administrator")
                self.__add_user("pharmacist", "pharma123", "Pharmacist")
            if self.__conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0] == 0:
                def d(days):
                    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
                samples = [
                    ("D001", "Paracetamol 500mg", "Tablet", "GSK", 25.00, 150, d(400)),
                    ("D002", "Amoxicillin 250mg", "Capsule", "Getz Pharma", 85.50, 80, d(300)),
                    ("D003", "Cough Syrup", "Syrup", "Searle", 120.00, 8, d(200)),
                    ("D004", "Insulin Glargine", "Injection", "Novo Nordisk", 1850.00, 5, d(90)),
                    ("D005", "Ibuprofen 400mg", "Tablet", "Abbott", 40.00, 60, d(500)),
                    ("D006", "Cetirizine 10mg", "Tablet", "Hilton Pharma", 30.00, 12, d(250)),
                    ("D007", "Omeprazole 20mg", "Capsule", "Pfizer", 95.00, 45, d(365)),
                    ("D008", "Vitamin C Syrup", "Syrup", "Sami Pharma", 150.00, 30, d(-45)),
                    ("D009", "Hydrocortisone Cream", "Ointment", "Bayer", 210.00, 20, d(180)),
                    ("D010", "Ciprofloxacin 500mg", "Tablet", "Bosch Pharma", 150.00, 4, d(-10)),
                    ("D011", "Eye Drops", "Drops", "Allergan", 175.00, 25, d(60)),
                ]
                self.__conn.executemany(
                    "INSERT INTO drugs VALUES (?, ?, ?, ?, ?, ?, ?)", samples
                )
                # a few old sales so the dashboard and reports are not empty
                old_sales = [("D001", "Paracetamol 500mg", 40, 25.0, -6), ("D005", "Ibuprofen 400mg", 25, 40.0, -5),
                             ("D002", "Amoxicillin 250mg", 12, 85.5, -3), ("D001", "Paracetamol 500mg", 20, 25.0, -2),
                             ("D006", "Cetirizine 10mg", 8, 30.0, -1)]
                for drug_id, name, qty, price, days in old_sales:
                    self.__conn.execute(
                        "INSERT INTO sales (drug_id, drug_name, quantity, unit_price, total_price, sale_date, sold_by) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (drug_id, name, qty, price, qty * price, d(days) + " 10:30:00", "admin"))

    # ------------------------------------------------------------- users
    def verify_user(self, username, password):
        """Return the user's full name if the login is correct, else None."""
        row = self.__conn.execute(
            "SELECT full_name, password_hash, salt FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        if row and hmac.compare_digest(self.__hash(password, row["salt"]), row["password_hash"]):
            return row["full_name"]
        return None

    # ------------------------------------------------------------- drugs
    def drug_exists(self, drug_id):
        row = self.__conn.execute("SELECT 1 FROM drugs WHERE drug_id = ?", (drug_id,)).fetchone()
        return row is not None

    def insert_drug(self, values):
        with self.__conn:
            self.__conn.execute("INSERT INTO drugs VALUES (?, ?, ?, ?, ?, ?, ?)", values)

    def update_drug(self, values):
        """values = (id, name, category, manufacturer, price, quantity, expiry)."""
        with self.__conn:
            cur = self.__conn.execute(
                "UPDATE drugs SET name=?, category=?, manufacturer=?, price=?, "
                "quantity=?, expiry_date=? WHERE drug_id=?",
                values[1:] + (values[0],),
            )
        return cur.rowcount

    def delete_drug(self, drug_id):
        with self.__conn:
            cur = self.__conn.execute("DELETE FROM drugs WHERE drug_id = ?", (drug_id,))
        return cur.rowcount

    def get_drug(self, drug_id):
        return self.__conn.execute("SELECT * FROM drugs WHERE drug_id = ?", (drug_id,)).fetchone()

    def get_all_drugs(self):
        return self.__conn.execute("SELECT * FROM drugs ORDER BY name").fetchall()

    def search_drugs(self, keyword):
        like = f"%{keyword}%"
        return self.__conn.execute(
            "SELECT * FROM drugs WHERE drug_id LIKE ? OR name LIKE ? ORDER BY name",
            (like, like),
        ).fetchall()

    def set_quantity(self, drug_id, quantity):
        with self.__conn:
            self.__conn.execute("UPDATE drugs SET quantity = ? WHERE drug_id = ?", (quantity, drug_id))

    # ------------------------------------------------------------- sales
    def record_sale(self, drug_id, name, quantity, unit_price, total, sold_by):
        """Reduce stock and save the sale together (one transaction).
        Returns False if there was not enough stock."""
        with self.__conn:
            cur = self.__conn.execute(
                "UPDATE drugs SET quantity = quantity - ? WHERE drug_id = ? AND quantity >= ?",
                (quantity, drug_id, quantity),
            )
            if cur.rowcount == 0:
                return False
            self.__conn.execute(
                "INSERT INTO sales (drug_id, drug_name, quantity, unit_price, total_price, "
                "sale_date, sold_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (drug_id, name, quantity, unit_price, total,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sold_by),
            )
        return True

    def get_sales(self):
        return self.__conn.execute(
            "SELECT sale_id, sale_date, drug_id, drug_name, quantity, unit_price, "
            "total_price, sold_by FROM sales ORDER BY sale_id DESC"
        ).fetchall()

    def total_revenue(self):
        return self.__conn.execute("SELECT COALESCE(SUM(total_price), 0) FROM sales").fetchone()[0]

    def close(self):
        self.__conn.close()
