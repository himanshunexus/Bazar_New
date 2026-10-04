from decimal import Decimal

from apps.products.models import Product

CART_SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(CART_SESSION_KEY, {})

    def add(self, product_id, quantity=1):
        key = str(product_id)
        self.data[key] = max(1, int(self.data.get(key, 0)) + int(quantity))
        self.save()

    def update(self, product_id, quantity):
        key = str(product_id)
        quantity = int(quantity)
        if quantity <= 0:
            self.data.pop(key, None)
        else:
            self.data[key] = quantity
        self.save()

    def remove(self, product_id):
        self.data.pop(str(product_id), None)
        self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.session.modified = True

    def save(self):
        self.session[CART_SESSION_KEY] = self.data
        self.session.modified = True

    def items(self):
        ids = [int(pk) for pk in self.data.keys()]
        products = Product.objects.select_related("shop").filter(id__in=ids, is_active=True)
        product_map = {product.id: product for product in products}
        for product_id in ids:
            product = product_map.get(product_id)
            if not product:
                continue
            quantity = int(self.data[str(product_id)])
            yield {
                "product": product,
                "quantity": quantity,
                "line_total": product.price * quantity,
            }

    def grouped_by_shop(self):
        groups = {}
        for item in self.items():
            shop = item["product"].shop
            bucket = groups.setdefault(shop.id, {"shop": shop, "items": [], "subtotal": Decimal("0.00")})
            bucket["items"].append(item)
            bucket["subtotal"] += item["line_total"]
        return groups.values()

    def total(self):
        return sum((item["line_total"] for item in self.items()), Decimal("0.00"))

    def __len__(self):
        return sum(int(qty) for qty in self.data.values())

    def product_ids(self):
        return [int(pk) for pk in self.data.keys()]
