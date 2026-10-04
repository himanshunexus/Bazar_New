import csv
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import Product

REQUIRED_HEADERS = ["name", "price", "stock", "unit_label", "category", "description", "mrp", "is_active"]


class CsvImportError(ValueError):
    def __init__(self, row_errors):
        super().__init__("CSV import failed")
        self.row_errors = row_errors


def validate_csv(file_obj):
    decoded = file_obj.read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded)
    if reader.fieldnames != REQUIRED_HEADERS:
        return [], [{"row": 1, "error": f"Header must be: {', '.join(REQUIRED_HEADERS)}"}]

    rows = []
    errors = []
    for row_num, row in enumerate(reader, start=2):
        if row_num > 1001:
            errors.append({"row": row_num, "error": "Maximum 1000 products per import."})
            break
        try:
            price = Decimal(row["price"])
            stock = int(row["stock"])
            mrp = Decimal(row["mrp"]) if row["mrp"] else None
            if price < 0 or stock < 0 or (mrp is not None and mrp < 0):
                raise ValueError("price, mrp and stock must be non-negative")
        except (InvalidOperation, ValueError) as exc:
            errors.append({"row": row_num, "error": str(exc)})
            continue
        if not row["name"].strip():
            errors.append({"row": row_num, "error": "name is required"})
            continue
        rows.append(
            {
                "name": row["name"].strip(),
                "price": price,
                "stock": stock,
                "unit_label": row["unit_label"].strip() or "1 unit",
                "category": row["category"].strip(),
                "description": row["description"].strip(),
                "mrp": mrp,
                "is_active": row["is_active"].strip().lower() not in {"0", "false", "no"},
            }
        )
    return rows, errors


@transaction.atomic
def import_products(shop, file_obj):
    rows, errors = validate_csv(file_obj)
    if errors:
        raise CsvImportError(errors)
    products = []
    for row in rows:
        product = Product(shop=shop, **row)
        product.save()
        products.append(product)
    return products
