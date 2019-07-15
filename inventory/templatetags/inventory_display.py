from django import template
register = template.Library()


@register.filter
def add_asset_display_class(asset):
    if asset.out_of_stock():
        return 'class=outofstock'
    elif asset.needs_reorder():
        return 'class=needsreorder'
    elif asset.in_stock():
        return 'class=instock'
    else:
        return ""


@register.filter
def item_pluralize(value):
    if abs(value) == 1:
        return "item"
    else:
        return "items"


@register.filter
def abs_value(value):
    return abs(value)


@register.filter
def add_quantity_status(asset):
    if asset.out_of_stock():
        return 0, "Out of stock"
    elif asset.needs_reorder():
        return 1, "Low Stock"
    elif asset.in_stock():
        return 2, "In Stock"
    else:
        return 3, "Unknown"
