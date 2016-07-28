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
