from odoo import models, fields, api, _

class AgreementInherit(models.Model):
    _inherit = 'agreement'
    
    property_id = fields.Many2one('product.product', string='Property', domain=[('is_property', '=', True)])
    property_book_for = fields.Selection(string='Property Transaction', selection=[('sale', 'Sale'), ('rent', 'Rent')])
    