# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Accounting Fiscal Year",

    "author": "Softhealer Technologies",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "1.1.4",

    "category": "Accounting",

    "summary": "Manage Fiscal Year, Account Fiscal Year App,  Close Fiscal Year, Cancel Closing Entry,Accounting Fiscal Period Module, Fiscal Year Opening Entry, Fiscal Year Closing Entry, Generate Fiscal Year Periods, Close Fiscal Year Period Odoo",

    "description": """
    Do you want to manage your fiscal year based on the financial rule of your country? A fiscal year system created for those countries where opening/closing entries are different or government accounting purposes are not the same as a calendar year. This module helps to manage fiscal years, You can generate opening and closing entries for the fiscal year. You can create your own fiscal year or you can generate a monthly or three month period for the fiscal year. You can close a fiscal year, cancel closing entries, or can close a particular period. Here income account, expense account default created for centralization & journal created with default debit and credit accounts. You can group by entries based on the fiscal year or period. Hurray!
Manage Accounting Fiscal Year Odoo
 Manage Fiscal Year Module, Account Fiscal Year, Accounting Fiscal Periods, Fiscal Year Opening Entry, Fiscal Year Closing Entry, Generate Fiscal Year Periods, Close Fiscal Year, Cancel Closing Entry, Close Fiscal Year Period Odoo
Manage Fiscal Year, Account Fiscal Year App,  Close Fiscal Year, Cancel Closing Entry,Accounting Fiscal Period Module, Fiscal Year Opening Entry, Fiscal Year Closing Entry, Generate Fiscal Year Periods, Close Fiscal Year Period Odoo


    """,

    "depends": ['account'],

    "data": [
        "data/account_data.xml",
        "security/ir.model.access.csv",
        "security/sh_sync_fiscal_year_security.xml",
        "views/fiscal_year_view.xml",
        "wizard/generate_opening_entries.xml",
        "wizard/account_open_closed_fiscalyear_view.xml",
        "views/account_view.xml",

    ],

    "images": ["static/description/background.png", ],
    "live_test_url": "https://youtu.be/_WrrrEZJXgI",

    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "OPL-1",
    "price": "90",
    "currency": "EUR"
}
