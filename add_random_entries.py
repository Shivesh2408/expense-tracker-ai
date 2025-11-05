import random
from datetime import date, timedelta
from db import ExpenseDB
from categorizer import CategoryRules

# Sample descriptions for each category
DESCRIPTIONS = {
    "Food": [
        "Pizza from Domino's", "Burger at McDonald's", "Groceries from supermarket",
        "Dinner at restaurant", "Coffee at cafe", "Lunch at food court",
        "Breakfast sandwich", "Snacks from store", "Fast food meal",
        "Restaurant dinner", "Food delivery", "Grocery shopping"
    ],
    "Travel": [
        "Uber ride to office", "Taxi fare", "Bus ticket",
        "Train ticket", "Fuel for car", "Petrol station",
        "Ola ride home", "Airport taxi", "Metro card recharge",
        "Parking fee", "Car service", "Travel expenses"
    ],
    "Shopping": [
        "Amazon purchase", "Flipkart order", "Clothes from mall",
        "Electronics shopping", "Online shopping", "Mall shopping",
        "Book store", "Gift purchase", "Shopping spree",
        "Retail store", "Department store", "Online order"
    ],
    "Bills": [
        "Electricity bill", "Water bill", "Internet bill",
        "WiFi recharge", "Mobile recharge", "Phone bill",
        "Rent payment", "Utility bill", "Monthly subscription",
        "Cable TV bill", "Gas bill", "Internet plan"
    ],
    "Entertainment": [
        "Movie tickets", "Netflix subscription", "Spotify premium",
        "Gaming purchase", "Concert tickets", "Entertainment",
        "Streaming service", "Video game", "Movie night",
        "Music subscription", "Theater tickets", "Entertainment expense"
    ],
    "Health": [
        "Doctor visit", "Pharmacy medicine", "Hospital bill",
        "Gym membership", "Medical checkup", "Health insurance",
        "Medicine purchase", "Dental checkup", "Fitness class",
        "Vitamin supplements", "Health products", "Medical expense"
    ],
    "Other": [
        "Misc expense", "Unknown purchase", "General expense",
        "Various items", "Other purchase", "Miscellaneous",
        "Random expense", "General shopping", "Other items"
    ]
}

def add_random_entries(count=200):
    db = ExpenseDB(db_path="expenses.db")
    rules = CategoryRules(path="categories.json")
    
    # Generate dates over the past 6 months
    today = date.today()
    start_date = today - timedelta(days=180)  # 6 months ago
    
    added = 0
    for i in range(count):
        # Random date within last 6 months
        days_ago = random.randint(0, 180)
        expense_date = today - timedelta(days=days_ago)
        
        # Random category
        category = random.choice(list(DESCRIPTIONS.keys()))
        
        # Random description from that category
        description = random.choice(DESCRIPTIONS[category])
        
        # Random amount (different ranges for different categories)
        if category == "Food":
            amount = round(random.uniform(50, 1500), 2)
        elif category == "Travel":
            amount = round(random.uniform(30, 800), 2)
        elif category == "Shopping":
            amount = round(random.uniform(100, 5000), 2)
        elif category == "Bills":
            amount = round(random.uniform(200, 5000), 2)
        elif category == "Entertainment":
            amount = round(random.uniform(100, 2000), 2)
        elif category == "Health":
            amount = round(random.uniform(150, 3000), 2)
        else:
            amount = round(random.uniform(50, 1000), 2)
        
        # Add the expense
        db.add_expense(
            date_iso=expense_date.isoformat(),
            amount=amount,
            description=description,
            category=category
        )
        added += 1
        
        if (i + 1) % 50 == 0:
            print(f"Added {i + 1}/{count} entries...")
    
    print(f"\nSuccessfully added {added} random expense entries!")
    print(f"Date range: {start_date.isoformat()} to {today.isoformat()}")

if __name__ == "__main__":
    add_random_entries(200)

