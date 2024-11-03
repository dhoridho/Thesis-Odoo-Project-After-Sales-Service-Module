# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2020 Hashmicro
#    (<http://www.hashmicro.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#
##############################################################################
{
    'name': 'Integration ODOO - PEPPOL',
    'version': '1.1.9',
    'author': "Hashmicro/JokoWa",
    'sequence': 1,
    'website': "http://www.hashmicro.com",
    'images':  [],
    'license': 'AGPL-3',
    'category': 'ODOO API',
    'summary': 'Integration API ODOO - PEPPOL',
    'depends': ['base', 'account', 'mail', 'contacts', 'product'],
    'description': """Integration API ODOO - PEPPOL""",
    'demo': [],
    'test': [],
    'data': [
        'security/ir.model.access.csv',
        'views/account_invoice.xml',
        'views/product.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/mail_template.xml',
        'views/account_tax.xml',
        'wizard/get_invoice_peppol_wizard.xml',
        'wizard/peppol_onboarding_wizard.xml',
    ],
    'css': [],
    'js': [],
    'price': 00.00,
    'currency': '',
    'installable': True,
    'application': False,
    'auto_install': False,
}
