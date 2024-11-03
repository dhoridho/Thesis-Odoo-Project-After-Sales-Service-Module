from odoo import api, fields, models,_
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_dropship = fields.Boolean(string='Is Dropship', readonly=True)
    customer_partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', readonly=True)
    customer_location_partner_id = fields.Many2one(comodel_name='res.partner', string='Customer Location', readonly=True)
    so_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', readonly=True)