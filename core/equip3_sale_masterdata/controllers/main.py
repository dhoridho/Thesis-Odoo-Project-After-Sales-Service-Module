# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http,fields
from odoo.http import request
# import json
# import base64

# from odoo import fields, api, SUPERUSER_ID
# from odoo.addons.sh_vendor_signup.controllers.main import CreateVendor
from odoo.addons.web.controllers.main import ExcelExport


class ExcelExportInherit(ExcelExport):

    def from_data(self, fields, rows):
        # merubah header saat export customer / vendor
        if http.request.context.get('res_partner') and not http.request.context.get('skip'):
            fields = ['ID','Display Name', 'Phone', 'Mobile', 'Email', 'Country', 'City', 'Company', 'Is a Vendor', 'Is a Customer']
        res = super().from_data(fields, rows)
        return res