from django import template

register = template.Library()

@register.filter
def get_index(lst, index):
    try:
        return lst[index]
    except:
        return None 