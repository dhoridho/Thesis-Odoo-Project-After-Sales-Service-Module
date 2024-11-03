# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    print_image = fields.Boolean('Print Image', help="""If Checked, you can see the product image in report""")
    image_sizes = fields.Selection([
        ('image_512', 'Big sized Image'), 
        ('image_256', 'Medium Sized Image'),
        ('image_128', 'Small Sized Image')],
        'Image Sizes', default="image_128", help="Image size to be displayed in report")
