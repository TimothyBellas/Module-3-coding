"""A small in-memory CRUD application for managing contacts."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Contact:
    """Represents one contact in the contact manager."""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    favorite: bool = False


_contacts: list[Contact] = []
_next_id = 1


def _required_text(value: str, field_name: str) -> str:
    """Return a stripped required string or raise a helpful error."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _normalize_email(email: str) -> str:
    """Normalize an email so lookups and uniqueness are case-insensitive."""
    return _required_text(email, "email").lower()


def add_contact(
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str] = None,
) -> Contact:
    """Add and return a contact. Email addresses must be unique."""
    global _next_id

    first_name = _required_text(first_name, "first_name")
    last_name = _required_text(last_name, "last_name")
    email = _normalize_email(email)

    if find_contact(email) is not None:
        raise ValueError(f"A contact with email {email!r} already exists")

    if phone is not None:
        phone = _required_text(phone, "phone")

    contact = Contact(
        id=_next_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    _contacts.append(contact)
    _next_id += 1
    return contact


def list_contacts() -> list[Contact]:
    """Return all contacts sorted by last name, then first name."""
    return sorted(
        _contacts,
        key=lambda contact: (
            contact.last_name.casefold(),
            contact.first_name.casefold(),
            contact.id,
        ),
    )


def find_contact(email: str) -> Optional[Contact]:
    """Return the contact with the given email, or None when not found."""
    normalized_email = _normalize_email(email)
    return next(
        (contact for contact in _contacts if contact.email == normalized_email),
        None,
    )


def update_phone(email: str, new_phone: Optional[str]) -> Contact:
    """Update a contact's phone number and return the updated contact."""
    contact = find_contact(email)
    if contact is None:
        raise LookupError(f"No contact found with email {_normalize_email(email)!r}")

    if new_phone is not None:
        new_phone = _required_text(new_phone, "new_phone")
    contact.phone = new_phone
    return contact


def toggle_favorite(email: str) -> Contact:
    """Flip a contact's favorite status and return the updated contact."""
    contact = find_contact(email)
    if contact is None:
        raise LookupError(f"No contact found with email {_normalize_email(email)!r}")

    contact.favorite = not contact.favorite
    return contact


def delete_contact(email: str) -> Contact:
    """Delete and return a contact, or raise LookupError when not found."""
    contact = find_contact(email)
    if contact is None:
        raise LookupError(f"No contact found with email {_normalize_email(email)!r}")

    _contacts.remove(contact)
    return contact


def _print_contacts(title: str) -> None:
    """Print the current contact list for the demonstration."""
    print(f"\n{title}")
    print("-" * len(title))
    for contact in list_contacts():
        favorite = "yes" if contact.favorite else "no"
        phone = contact.phone or "not provided"
        print(
            f"#{contact.id}: {contact.first_name} {contact.last_name} | "
            f"{contact.email} | {phone} | favorite: {favorite}"
        )


def demo() -> None:
    """Demonstrate create, read, update, toggle, and delete operations."""
    print("Adding contacts...")
    add_contact("Maya", "Chen", "maya.chen@example.com", "555-0101")
    add_contact("Liam", "Anderson", "liam.anderson@example.com")
    add_contact("Sofia", "Patel", "sofia.patel@example.com", "555-0103")
    add_contact("Noah", "Brown", "noah.brown@example.com", "555-0104")
    add_contact("Ava", "Garcia", "ava.garcia@example.com", "555-0105")
    add_contact("Ethan", "Williams", "ethan.williams@example.com")

    _print_contacts("All contacts (sorted by last name)")

    print("\nFinding Sofia by email:")
    print(find_contact("sofia.patel@example.com"))

    print("\nUpdating Liam's phone number...")
    print(update_phone("liam.anderson@example.com", "555-0199"))

    print("\nToggling favorites for Maya and Ava...")
    print(toggle_favorite("maya.chen@example.com"))
    print(toggle_favorite("ava.garcia@example.com"))

    print("\nDeleting Noah...")
    print(delete_contact("noah.brown@example.com"))

    _print_contacts("Final contacts")


if __name__ == "__main__":
    demo()
