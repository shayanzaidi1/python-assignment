"""
inventory.py
------------
Inventory manages drug records and stock levels.  It uses the Database class
and returns Drug objects, so the GUI never touches SQL.
"""
from database import BaseManager
from drug import Drug


class Inventory(BaseManager):
    # ------------------------------------------------------- drug records
    def add_drug(self, drug):
        if self._db.drug_exists(drug.drug_id):
            raise ValueError(f"Drug ID '{drug.drug_id}' already exists. Use a different ID.")
        self._db.insert_drug(drug.to_tuple())

    def update_drug(self, drug):
        if self._db.update_drug(drug.to_tuple()) == 0:
            raise ValueError(f"No medicine with ID '{drug.drug_id}' was found.")

    def delete_drug(self, drug_id):
        if self._db.delete_drug(drug_id) == 0:
            raise ValueError(f"No medicine with ID '{drug_id}' was found.")

    def get_drug(self, drug_id):
        row = self._db.get_drug(drug_id)
        return Drug.from_row(row) if row else None

    def get_all(self):
        return [Drug.from_row(r) for r in self._db.get_all_drugs()]

    def search(self, keyword):
        keyword = keyword.strip()
        if not keyword:
            return self.get_all()
        return [Drug.from_row(r) for r in self._db.search_drugs(keyword)]

    # ---------------------------------------------------------- stock work
    def adjust_stock(self, drug_id, change):
        """Add (positive) or remove (negative) stock. Never goes below zero."""
        drug = self.get_drug(drug_id)
        if drug is None:
            raise ValueError("Please select a medicine first.")
        new_quantity = drug.quantity + change
        if new_quantity < 0:
            raise ValueError(f"Cannot remove {abs(change)} units. Only {drug.quantity} in stock.")
        self._db.set_quantity(drug_id, new_quantity)
        return new_quantity

    def low_stock(self):
        return [d for d in self.get_all() if d.is_low_stock() and not d.is_expired()]

    def expired(self):
        return [d for d in self.get_all() if d.is_expired()]

    def stats(self):
        drugs = self.get_all()
        return {
            "total": len(drugs),
            "available_stock": sum(d.quantity for d in drugs if not d.is_expired()),
            "low_stock": sum(1 for d in drugs if d.is_low_stock() and not d.is_expired()),
            "expired": sum(1 for d in drugs if d.is_expired()),
        }

    def summary(self):
        s = self.stats()
        return (f"Inventory: {s['total']} medicines, {s['available_stock']} units in stock, "
                f"{s['low_stock']} low-stock, {s['expired']} expired.")
