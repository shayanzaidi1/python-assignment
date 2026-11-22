# PharmaCare - Drug Management System

A desktop pharmacy application built with **Python OOP**, **Tkinter** and **SQLite**.

## Requirements
- Python 3.8 or newer (https://www.python.org/downloads/)
- Tkinter (included with Python on Windows and macOS)
  - Ubuntu/Debian only: `sudo apt install python3-tk`
- No extra packages are needed.

## Project structure
```
DrugManagementSystem/
├── main.py        # starts the application
├── database.py    # Database class (all SQLite code) + BaseManager parent class
├── drug.py        # Drug class + Tablet, Syrup, Injection child classes
├── inventory.py   # Inventory class (records + stock)
├── sales.py       # Sales class (selling + revenue)
├── login.py       # Login class (authentication)
├── gui.py         # All Tkinter screens + DrugManagementSystem class
├── widgets.py     # Dark/light themes, rounded Card and Pill widgets, icons
└── README.md
```
`pharmacy.db` is created automatically on the first run (with sample medicines).

## How to run in VS Code
1. Install Python and the **Python** extension in VS Code.
2. Create a folder `DrugManagementSystem` and put all eight `.py` files and this README inside it.
3. In VS Code: **File > Open Folder...** and choose `DrugManagementSystem`.
4. Open `main.py` and press the **Run (triangle)** button, or open the terminal
   (**Terminal > New Terminal**) and type:
   ```
   python main.py
   ```
   (on macOS/Linux use `python3 main.py`)

## Login accounts
| Username   | Password   |
|------------|------------|
| admin      | admin123   |
| pharmacist | pharma123  |

Three wrong attempts close the application. Passwords are stored as salted SHA-256 hashes.

## Using the system
- **Dashboard** - total medicines, available stock, low-stock and expired counts, plus both monitoring tables.
- **Medicines** - fill the form and press **Add**. Click a row to load it, edit, then **Update**; **Delete** removes it; **Clear** empties the form; the search bar finds by name or ID.
- **Inventory** - choose a medicine, enter an amount, **Increase** or **Decrease** stock (it can never go below 0).
- **Sales** - choose a medicine, enter a quantity; the total is calculated automatically. Expired medicines and quantities above stock are rejected.
- **Reports** - all medicines, low-stock, expired, sales history, total revenue, and **Export CSV**.

Row colours: **red** = expired, **orange** = low stock (10 units or fewer).

The design has a **dark theme (default) and a light theme**. Click the sun/moon button in the top bar to switch. It uses rounded cards, a violet/cyan gradient, icons, a stock chart, a 7-day sales chart, a stock-status donut chart, top-selling medicines and a stock-health card. The bell shows how many medicines need attention.

## Validation rules
- All fields are required. Drug IDs must be unique (letters, numbers, `-`).
- Price must be a number greater than 0. Quantity must be a whole number, 0 or more.
- Expiry date must be `YYYY-MM-DD` (e.g. `2027-05-30`).
- All SQL uses parameterized queries (`?`).

## OOP concepts in this project
| Concept | Where | How |
|---|---|---|
| **Encapsulation** | `drug.py`, `database.py`, `login.py` | Drug attributes are protected (`_price`) and changed only through validated `@property` setters. The database connection (`__conn`) and login state (`__username`) are private. |
| **Inheritance** | `drug.py`, `database.py`, `gui.py` | `Tablet`, `Syrup`, `Injection` inherit from `Drug`. `Inventory` and `Sales` inherit from `BaseManager`. All pages inherit from `BasePage`; `Card` and `Pill` (in `widgets.py`) inherit from `tk.Canvas`; `LoginWindow` and `DrugManagementSystem` inherit from `tk.Tk`. |
| **Polymorphism** | `drug.py`, `inventory.py`, `sales.py`, `gui.py` | `describe()` and `storage_advice()` behave differently in each drug class; `summary()` differs in `Inventory` and `Sales`; every page overrides `build()` and `refresh()` and the main window calls `page.refresh()` on any page. |
| **Abstraction** | `database.py` | `BaseManager` is an abstract class (`ABC`). The GUI calls simple methods such as `inventory.add_drug()` or `sales.sell()` and never sees SQL. |

## If the window looks blurry
The program already asks Windows for a sharp (DPI-aware) window in `main.py`, so it stays crisp at 125% / 150% display scaling.

## Resetting the data
Close the app and delete `pharmacy.db`. It will be recreated with the sample medicines and sample sales.
(If you ran an older version of this project, delete the old `pharmacy.db` once.)
