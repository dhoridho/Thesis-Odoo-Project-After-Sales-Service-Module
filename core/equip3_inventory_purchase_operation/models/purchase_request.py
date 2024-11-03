from odoo import _, api, fields, models
import json

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    procurement_planning_id = fields.Many2one(comodel_name='procurement.planning.model', string='Procurement Planning', ondelete='cascade')
    
    @api.model
    def create(self, vals):
        if vals.get('procurement_planning_id'):
            procurement_planning = self.env['procurement.planning.model'].browse(vals['procurement_planning_id'])
            procurement_planning.state = 'in_progress'

        return super(PurchaseRequest, self).create(vals)
    
class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'
    
    product_id_domain = fields.Char('Product Domain', compute="compute_product_id_domain")
    
    @api.depends('request_id.procurement_planning_id')
    def compute_product_id_domain(self):
        self.product_id_domain = False
        procurement_planning = self.request_id.procurement_planning_id
        if procurement_planning:
            product_ids = procurement_planning.procurement_line.mapped('product_id').ids
            self.product_id_domain = json.dumps([('id', 'in', product_ids)]) if product_ids else json.dumps([('id', 'in', [])])
