#  -*- encoding: utf-8 -*-

{
    "name": "Leave Constraints",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ['sg_holiday_extended'],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
Configuration Settings for different MOM standard leaves in singapore
============================
List of constraints and checks as below
you can not request for leave over cessation date.
can not request for leave before Number of days set in leave configuration
can not apply for leave, if your requested date is not before 2 month before
date, and your dependent is not Singaporean.
constraint calls when your requested leave year is not current year.
can not apply for Extended Child Care Leave, Paid Child Care Leave,
Unpaid Infant Care Leave and Paternity Leave if no child dependent found in
your dependents.
can not create public holiday for different year.
can not create multiple public holiday for same year.
    """,
    "summary": """
Configuration Settings for different MOM standard leaves in singapore
    """,
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 39,
    "currency": 'EUR',
}
