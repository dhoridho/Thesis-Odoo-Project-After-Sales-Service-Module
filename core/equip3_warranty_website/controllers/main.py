# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request

class WarrantyInformation(http.Controller):
    @http.route(['/page/warranty_information'], auth='public', website=True, csrf=True)
    def warranty_information(self, **kw):
        product = kw.get('product')
        product = product.split('/?serial=')[0]
        product_warranty = request.env['product.warranty'].sudo().browse(int(product))
        values = {
            'product_warranty': product_warranty
        }
        return request.render('equip3_warranty_website.warranty_information', values)