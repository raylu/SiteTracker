from django import template
from sitemngr.models import System
from sitemngr import util

register = template.Library()

@register.filter(name='graphname')
def graphname(value):
    if not util.is_system(value):
        return '{} (?)'.format(value)
    r = util.get_wormhole_class(value)
    if r and not r == 0:
        return '{} ({})'.format(value, r)
    else:
        s = System.objects.get(name=value)
        status = float(s.security_level)
        if status >= 0.45:
            return '{} (H)'.format(value)
        elif status > 0.0:
            return '{} (L)'.format(value)
        else:
            return '{} (N)'.format(value)
    return '{} (.)'.format(value)
