from django import template
import math

register = template.Library()

def foliation(value):
    if value is None:
        return ""
    valueRnd = math.floor(float(value))
    valueRemaining = float(value) - valueRnd;

    retStr = str(valueRnd)
    if valueRemaining > 0.09 and valueRemaining  < 0.11:
        retStr += 'r'
    elif valueRemaining > 0.19 and valueRemaining  < 0.21:
        retStr += 'v'

    return retStr

register.filter('foliation', foliation)