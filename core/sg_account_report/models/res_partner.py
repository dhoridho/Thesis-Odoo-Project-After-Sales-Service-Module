
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_uen = fields.Char('Customer UEN')
    customer_id = fields.Char('Customer ID')
    supplier_uen = fields.Char('Supplier UEN')

    _sql_constraints = [
        ('customer_id_uniq', 'unique(customer_id)',
         'Customer ID must be unique per Customer!'),
    ]
