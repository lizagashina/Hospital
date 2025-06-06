from django import template
from datetime import date

register = template.Library()

def pluralize_ru(number, forms):
    if 11 <= number % 100 <= 14:
        return forms[2]
    elif number % 10 == 1:
        return forms[0]
    elif 2 <= number % 10 <= 4:
        return forms[1]
    else:
        return forms[2]

@register.filter
def age_in_years(birth_date):
    if not birth_date:
        return ''

    today = date.today()
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day

    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12

    year_word = pluralize_ru(years, ['год', 'года', 'лет'])
    month_word = pluralize_ru(months, ['месяц', 'месяца', 'месяцев'])

    return f"{years} {year_word} {months} {month_word}"
