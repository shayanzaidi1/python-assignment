"""
sales.py
--------
Sales handles selling medicines and calculating revenue.
"""
from datetime import date, timedelta

from database import BaseManager


class Sales(BaseManager):
    def __init__(self, database, inventory):
        super().__init__(database)
        self._inventory = inventory

    def calculate_total(self, drug, quantity):
        return round(drug.price * quantity, 2)

    def sell(self, drug_id, quantity, sold_by="admin"):
        """Validate and complete a sale. Returns the total price."""
        try:
            quantity = int(str(quantity).strip())
        except ValueError:
            raise ValueError("Quantity must be a whole number.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        drug = self._inventory.get_drug(drug_id)
        if drug is None:
            raise ValueError("Please select a medicine to sell.")
        if drug.is_expired():
            raise ValueError(f"{drug.name} is expired and cannot be sold.")
        if quantity > drug.quantity:
            raise ValueError(f"Not enough stock. Only {drug.quantity} units of {drug.name} available.")

        total = self.calculate_total(drug, quantity)
        if not self._db.record_sale(drug.drug_id, drug.name, quantity, drug.price, total, sold_by):
            raise ValueError("The sale failed because the stock changed. Please try again.")
        return total

    def history(self):
        return [tuple(row) for row in self._db.get_sales()]

    def top_selling(self, limit=3):
        """Best-selling medicines as a list of (name, units sold, money)."""
        totals = {}
        for sale in self.history():          # sale = (id, date, drug_id, name, qty, price, total, by)
            units, money = totals.get(sale[3], (0, 0))
            totals[sale[3]] = (units + sale[4], money + sale[6])
        ranked = sorted(totals.items(), key=lambda item: item[1][0], reverse=True)
        return [(name, units, money) for name, (units, money) in ranked[:limit]]

    def daily_totals(self, days=7):
        """Money earned on each of the last `days` days, as [(day name, total)]."""
        totals = {}
        for sale in self.history():
            totals[sale[1][:10]] = totals.get(sale[1][:10], 0) + sale[6]
        result = []
        for back in range(days - 1, -1, -1):
            day = date.today() - timedelta(days=back)
            result.append((day.strftime("%a"), totals.get(day.strftime("%Y-%m-%d"), 0)))
        return result

    def total_revenue(self):
        return self._db.total_revenue()

    def summary(self):
        return f"Sales: {len(self.history())} transactions, revenue Rs. {self.total_revenue():,.2f}."
