from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warranty_start_date = fields.Date('Warranty Start Date')
    warranty_end_date = fields.Date('Warranty End Date')
