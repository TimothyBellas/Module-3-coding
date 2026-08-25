from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker # type: ignore


# echo=True prints each SQL statement so database activity is visible.
engine = create_engine("sqlite:///product_catalog.db", echo=True)

# Base is the parent class for every model, and Session manages database work.
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Category(Base):
    """A product category stored in the categories table."""

    __tablename__ = "categories"

    # Category names must be present and cannot be repeated.
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    def __repr__(self):
        # Return a readable value when a category is printed.
        return (
            f"Category(id={self.id}, name={self.name!r}, "
            f"description={self.description!r})"
        )


class Product(Base):
    """A catalog product stored in the products table."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True)

    # Store the category name as plain text until relationships are introduced.
    category_name = Column(String)

    def __repr__(self):
        # Format prices to two decimal places in printed query results.
        return (
            f"Product(id={self.id}, name={self.name!r}, price=${self.price:.2f}, "
            f"in_stock={self.in_stock}, category_name={self.category_name!r})"
        )


# Create the tables if they do not already exist.
Base.metadata.create_all(engine)


def seed_database(session):
    """Insert the sample categories and products when they are missing."""

    categories = [
        Category(name="Electronics", description="Electronic devices and accessories"),
        Category(name="Books", description="Printed books and reference materials"),
        Category(name="Home", description="Products for the home"),
    ]

    products = [
        Product(name="Wireless Mouse", price=24.99, in_stock=True, category_name="Electronics"),
        Product(name="USB-C Hub", price=39.99, in_stock=True, category_name="Electronics"),
        Product(name="Mechanical Keyboard", price=89.99, in_stock=False, category_name="Electronics"),
        Product(name="Python Fundamentals", price=34.50, in_stock=True, category_name="Books"),
        Product(name="SQL Quick Reference", price=19.95, in_stock=True, category_name="Books"),
        Product(name="Desk Lamp", price=45.00, in_stock=False, category_name="Home"),
        Product(name="Storage Basket", price=17.50, in_stock=True, category_name="Home"),
    ]

    # Check existing names so rerunning the script does not duplicate seed data.
    existing_category_names = {
        name for (name,) in session.query(Category.name).all()
    }
    session.add_all(
        category for category in categories if category.name not in existing_category_names
    )

    existing_product_names = {name for (name,) in session.query(Product.name).all()}
    session.add_all(
        product for product in products if product.name not in existing_product_names
    )

    # Commit both sets of inserts as one transaction.
    session.commit()


def print_query_results(session):
    """Run and print the three requested catalog queries."""

    # Query 1: every category, ordered by its primary key.
    print("\nAll categories:")
    for category in session.query(Category).order_by(Category.id).all():
        print(category)

    # Query 2: only products whose in_stock value is true.
    print("\nProducts in stock:")
    for product in (
        session.query(Product)
        .filter(Product.in_stock.is_(True))
        .order_by(Product.id)
        .all()
    ):
        print(product)

    # Query 3: products with a price strictly below $50.
    print("\nProducts under $50:")
    for product in (
        session.query(Product).filter(Product.price < 50).order_by(Product.price).all()
    ):
        print(product)


if __name__ == "__main__":
    # The context manager closes the session automatically when finished.
    with Session() as session:
        seed_database(session)
        print_query_results(session)
