from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def inr(value):
    try:
        amount = Decimal(value)
    except Exception:
        amount = Decimal("0.00")
    return f"Rs {amount:,.2f}"
