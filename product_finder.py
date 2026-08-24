# product_finder.py

import sqlite3


# --------------------------------------------------
# Create an in-memory SQLite database
# --------------------------------------------------
connection = sqlite3.connect(":memory:")
cursor = connection.cursor()


# --------------------------------------------------
# Create the products table
# --------------------------------------------------
cursor.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    rating REAL,
    in_stock INTEGER DEFAULT 1
)
""")


# --------------------------------------------------
# Insert product data
# --------------------------------------------------
products = [
    ("Wireless Mouse", "Accessories", 29.99, 4.5, 1),
    ("Mechanical Keyboard", "Accessories", 89.99, 4.8, 1),
    ("USB-C Hub", "Accessories", 34.99, 4.2, 0),
    ("27-inch Monitor", "Displays", 299.99, 4.6, 1),
    ("24-inch Monitor", "Displays", 179.99, 4.3, 1),
    ("Webcam HD", "Accessories", 49.99, 3.9, 1),
    ("Noise-Canceling Headphones", "Audio", 199.99, 4.7, 1),
    ("Bluetooth Speaker", "Audio", 59.99, 4.1, 0),
    ("Laptop Stand", "Accessories", 39.99, 4.4, 1),
    ("External SSD 1TB", "Storage", 89.99, 4.6, 1),
    ("External SSD 2TB", "Storage", 149.99, 4.5, 1),
    ("Flash Drive 64GB", "Storage", 12.99, 4.0, 1),
]

cursor.executemany("""
INSERT INTO products (name, category, price, rating, in_stock)
VALUES (?, ?, ?, ?, ?)
""", products)

connection.commit()


# ==================================================
# QUERY 1
# Which products are out of stock?
# Show name and category
# ==================================================
print("\n" + "=" * 70)
print("1. PRODUCTS OUT OF STOCK")
print("=" * 70)

cursor.execute("""
SELECT name, category
FROM products
WHERE in_stock = 0
""")

results = cursor.fetchall()

print(f"{'Name':<35} {'Category':<20}")
print("-" * 70)

for name, category in results:
    print(f"{name:<35} {category:<20}")


# ==================================================
# QUERY 2
# Rating of 4.5 or higher AND price under $100
# Show name, rating, and price
# ==================================================
print("\n" + "=" * 70)
print("2. HIGH-RATED PRODUCTS UNDER $100")
print("=" * 70)

cursor.execute("""
SELECT name, rating, price
FROM products
WHERE rating >= 4.5
AND price < 100
ORDER BY rating DESC
""")

results = cursor.fetchall()

print(f"{'Name':<35} {'Rating':<10} {'Price':>10}")
print("-" * 70)

for name, rating, price in results:
    print(f"{name:<35} {rating:<10.1f} ${price:>9.2f}")


# ==================================================
# QUERY 3
# 3 most expensive Accessories products
# Show name and price
# ==================================================
print("\n" + "=" * 70)
print("3. TOP 3 MOST EXPENSIVE ACCESSORIES")
print("=" * 70)

cursor.execute("""
SELECT name, price
FROM products
WHERE category = 'Accessories'
ORDER BY price DESC
LIMIT 3
""")

results = cursor.fetchall()

print(f"{'Name':<35} {'Price':>10}")
print("-" * 70)

for name, price in results:
    print(f"{name:<35} ${price:>9.2f}")


# ==================================================
# QUERY 4
# Products with "Monitor" in their name
# Show all columns
# ==================================================
print("\n" + "=" * 70)
print('4. PRODUCTS WITH "MONITOR" IN THE NAME')
print("=" * 70)

cursor.execute("""
SELECT *
FROM products
WHERE name LIKE '%Monitor%'
""")

results = cursor.fetchall()

print(
    f"{'ID':<5} "
    f"{'Name':<25} "
    f"{'Category':<15} "
    f"{'Price':>10} "
    f"{'Rating':>8} "
    f"{'Stock':>8}"
)
print("-" * 85)

for product_id, name, category, price, rating, in_stock in results:
    stock_status = "Yes" if in_stock == 1 else "No"

    print(
        f"{product_id:<5} "
        f"{name:<25} "
        f"{category:<15} "
        f"${price:>9.2f} "
        f"{rating:>8.1f} "
        f"{stock_status:>8}"
    )


# ==================================================
# QUERY 5
# Products NOT in Accessories and currently in stock
# Show name, category, and price
# Sort by category, then price
# ==================================================
print("\n" + "=" * 70)
print("5. IN-STOCK PRODUCTS NOT IN ACCESSORIES")
print("=" * 70)

cursor.execute("""
SELECT name, category, price
FROM products
WHERE category != 'Accessories'
AND in_stock = 1
ORDER BY category, price
""")

results = cursor.fetchall()

print(f"{'Name':<35} {'Category':<15} {'Price':>10}")
print("-" * 70)

for name, category, price in results:
    print(f"{name:<35} {category:<15} ${price:>9.2f}")


# --------------------------------------------------
# Close the database connection
# --------------------------------------------------
connection.close()

print("\n" + "=" * 70)
print("Database connection closed.")
print("=" * 70)
