from odoo import api, fields, models, _


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_purchase_order = fields.Boolean('Is Purchase Order', default= False)
    mrp_material_to_purchase_id = fields.Many2one(string='Material to Purchase')
    is_readonly_origin = fields.Boolean()


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    mrp_force_location_dest_id = fields.Many2one('stock.location', string='MRP Force Location')
 