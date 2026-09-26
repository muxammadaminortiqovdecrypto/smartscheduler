from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Dictionary dan qiymat olish"""
    return dictionary.get(key, [])
