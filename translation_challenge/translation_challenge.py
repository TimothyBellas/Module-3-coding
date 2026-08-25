"""Solve the same sales-analysis questions with both SQL and pandas."""

import sqlite3
from textwrap import dedent

import pandas as pd
from pandas.testing import assert_frame_equal


SALES_DATA = [
    ("Widget A", "Electronics", 29.99, 150, "2025-Q1"),
    ("Widget B", "Electronics", 49.99, 89, "2025-Q1"),
    ("Gadget X", "Accessories", 15.99, 300, "2025-Q1"),
    ("Widget A", "Electronics", 29.99, 200, "2025-Q2"),
    ("Gadget Y", "Accessories", 22.99, 175, "2025-Q2"),
    ("Widget C", "Electronics", 79.99, 50, "2025-Q2"),
    ("Gadget X", "Accessories", 15.99, 280, "2025-Q2"),
    ("Widget B", "Electronics", 49.99, 120, "2025-Q3"),
]

COLUMNS = ["product", "category", "unit_price", "quantity", "quarter"]


SQL_QUERIES = {
    "1. Total revenue per product": dedent(
        """
        SELECT product, ROUND(SUM(unit_price * quantity), 2) AS total_revenue
        FROM sales
        GROUP BY product
        ORDER BY product;
        """
    ).strip(),
    "2. Quarter with the highest total quantity sold": dedent(
        """
        SELECT quarter, SUM(quantity) AS total_quantity
        FROM sales
        GROUP BY quarter
        ORDER BY total_quantity DESC, quarter
        LIMIT 1;
        """
    ).strip(),
    "3. Average unit price per category": dedent(
        """
        SELECT category, ROUND(AVG(unit_price), 2) AS average_unit_price
        FROM sales
        GROUP BY category
        ORDER BY category;
        """
    ).strip(),
    "4. Products with total quantity over 200": dedent(
        """
        SELECT product, SUM(quantity) AS total_quantity
        FROM sales
        GROUP BY product
        HAVING SUM(quantity) > 200
        ORDER BY product;
        """
    ).strip(),
}


def create_dataframe() -> pd.DataFrame:
    """Load the source records into a pandas DataFrame."""
    return pd.DataFrame(SALES_DATA, columns=COLUMNS)


def create_database() -> sqlite3.Connection:
    """Load the source records into an in-memory SQLite database."""
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE sales (
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            quarter TEXT NOT NULL
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO sales (product, category, unit_price, quantity, quarter)
        VALUES (?, ?, ?, ?, ?)
        """,
        SALES_DATA,
    )
    connection.commit()
    return connection


def run_sql(connection: sqlite3.Connection, query: str) -> pd.DataFrame:
    """Execute SQL with sqlite3 and return a labeled DataFrame for comparison."""
    cursor = connection.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    return pd.DataFrame(rows, columns=column_names)


def pandas_solutions(sales_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return pandas solutions for all four analysis questions."""
    revenue_by_product = (
        sales_df.assign(revenue=sales_df["unit_price"] * sales_df["quantity"])
        .groupby("product", as_index=False)["revenue"]
        .sum()
        .rename(columns={"revenue": "total_revenue"})
        .sort_values("product", ignore_index=True)
    )
    revenue_by_product["total_revenue"] = revenue_by_product[
        "total_revenue"
    ].round(2)

    quantity_by_quarter = (
        sales_df.groupby("quarter", as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "total_quantity"})
        .sort_values(
            ["total_quantity", "quarter"],
            ascending=[False, True],
            ignore_index=True,
        )
        .head(1)
        .reset_index(drop=True)
    )

    average_price_by_category = (
        sales_df.groupby("category", as_index=False)["unit_price"]
        .mean()
        .rename(columns={"unit_price": "average_unit_price"})
        .sort_values("category", ignore_index=True)
    )
    average_price_by_category["average_unit_price"] = average_price_by_category[
        "average_unit_price"
    ].round(2)

    products_over_200 = (
        sales_df.groupby("product", as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "total_quantity"})
        .query("total_quantity > 200")
        .sort_values("product", ignore_index=True)
    )

    return {
        "1. Total revenue per product": revenue_by_product,
        "2. Quarter with the highest total quantity sold": quantity_by_quarter,
        "3. Average unit price per category": average_price_by_category,
        "4. Products with total quantity over 200": products_over_200,
    }


def print_side_by_side(
    title: str,
    query: str,
    sql_result: pd.DataFrame,
    pandas_result: pd.DataFrame,
) -> None:
    """Display the SQL and the two equivalent result tables side by side."""
    print(f"\n=== {title} ===")
    print("SQL:")
    print(query)
    comparison = pd.concat(
        [sql_result.add_prefix("SQL: "), pandas_result.add_prefix("pandas: ")],
        axis=1,
    )
    print("\nResults:")
    print(comparison.to_string(index=False))


def main() -> None:
    sales_df = create_dataframe()
    connection = create_database()

    try:
        pandas_results = pandas_solutions(sales_df)

        for title, query in SQL_QUERIES.items():
            sql_result = run_sql(connection, query)
            pandas_result = pandas_results[title]

            # Confirm that the two translations produce equivalent answers.
            assert_frame_equal(
                sql_result.reset_index(drop=True),
                pandas_result.reset_index(drop=True),
                check_dtype=False,
            )
            print_side_by_side(title, query, sql_result, pandas_result)

        # Bonus: pandas executes the first SQL query and returns a DataFrame.
        print("\n=== BONUS: SQL result loaded with pd.read_sql() ===")
        bonus_df = pd.read_sql(SQL_QUERIES["1. Total revenue per product"], connection)
        print(bonus_df.to_string(index=False))

        print("\nAll SQL and pandas results match.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
