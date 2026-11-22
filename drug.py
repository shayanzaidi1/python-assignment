"""
drug.py - the Drug class and its child classes.

Encapsulation : data is stored in protected attributes (_price ...) and changed
                only through properties that check the value first.
Inheritance   : Tablet, Syrup and Injection inherit from Drug.
Polymorphism  : describe() and storage_advice() differ in every child class.
"""
from datetime import date, datetime

DATE_FORMAT = "%Y-%m-%d"
LOW_STOCK_LIMIT = 10
CATEGORIES = ["Tablet", "Capsule", "Syrup", "Injection", "Ointment", "Drops", "Other"]
DATE_ERROR = "Expiry date must be in YYYY-MM-DD format (e.g. 2027-05-30)."


class Drug:
    def __init__(self, drug_id, name, category, manufacturer, price, quantity, expiry_date):
        self._drug_id = self._text(drug_id, "Drug ID").upper()
        if not self._drug_id.replace("-", "").isalnum():
            raise ValueError("Drug ID may contain only letters, numbers and '-'.")
        self._name = self._text(name, "Medicine name")
        self._category = self._text(category, "Category")
        self._manufacturer = self._text(manufacturer, "Manufacturer")
        self.price = price              # these three use the setters below
        self.quantity = quantity
        self.expiry_date = expiry_date

    @staticmethod
    def _text(value, label):
        value = str(value).strip()
        if not value:
            raise ValueError(f"{label} is required.")
        return value

    # ---- read-only properties
    @property
    def drug_id(self): return self._drug_id
    @property
    def name(self): return self._name
    @property
    def category(self): return self._category
    @property
    def manufacturer(self): return self._manufacturer

    # ---- properties with validation
    @property
    def price(self): return self._price

    @price.setter
    def price(self, value):
        try:
            number = float(self._text(value, "Price"))
        except ValueError:
            raise ValueError("Price must be a valid number greater than zero.")
        if number <= 0:
            raise ValueError("Price must be greater than zero.")
        self._price = round(number, 2)

    @property
    def quantity(self): return self._quantity

    @quantity.setter
    def quantity(self, value):
        try:
            number = int(self._text(value, "Quantity"))
        except ValueError:
            raise ValueError("Quantity must be a whole number.")
        if number < 0:
            raise ValueError("Quantity cannot be negative.")
        self._quantity = number

    @property
    def expiry_date(self): return self._expiry_date

    @expiry_date.setter
    def expiry_date(self, value):
        text = self._text(value, "Expiry date")
        try:
            parsed = datetime.strptime(text, DATE_FORMAT)
        except ValueError:
            raise ValueError(DATE_ERROR)
        if parsed.strftime(DATE_FORMAT) != text:     # rejects 2027-5-3
            raise ValueError(DATE_ERROR)
        self._expiry_date = text

    # ---- behaviour
    def is_expired(self):
        return datetime.strptime(self._expiry_date, DATE_FORMAT).date() < date.today()

    def is_low_stock(self):
        return self._quantity <= LOW_STOCK_LIMIT

    def status(self):
        if self.is_expired():
            return "Expired"
        return "Low Stock" if self.is_low_stock() else "OK"

    def to_tuple(self):
        return (self._drug_id, self._name, self._category, self._manufacturer,
                self._price, self._quantity, self._expiry_date)

    def describe(self):
        return f"{self._name} ({self._category}) by {self._manufacturer}"

    def storage_advice(self):
        return "Store in a cool, dry place away from sunlight."

    @staticmethod
    def create(drug_id, name, category, manufacturer, price, quantity, expiry_date):
        """Pick the right class from the category (Tablet, Syrup, Injection or Drug)."""
        drug_class = {"Tablet": Tablet, "Syrup": Syrup, "Injection": Injection}.get(str(category).strip(), Drug)
        return drug_class(drug_id, name, category, manufacturer, price, quantity, expiry_date)

    @staticmethod
    def from_row(row):
        return Drug.create(row["drug_id"], row["name"], row["category"], row["manufacturer"],
                           row["price"], row["quantity"], row["expiry_date"])


class Tablet(Drug):
    def describe(self):
        return f"{super().describe()} - oral tablet, take with water."

    def storage_advice(self):
        return "Tablet: keep below 25 C in a dry place."


class Syrup(Drug):
    def describe(self):
        return f"{super().describe()} - liquid syrup, shake well."

    def storage_advice(self):
        return "Syrup: keep the bottle closed; use within the period stated after opening."


class Injection(Drug):
    def describe(self):
        return f"{super().describe()} - injectable, use under medical supervision."

    def storage_advice(self):
        return "Injection: store in a refrigerator (2-8 C), do not freeze."
