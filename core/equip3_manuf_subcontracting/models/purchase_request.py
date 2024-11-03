from odoo import models, fields, api, _

    
class PurchaseRequestInherit(models.Model):
    _inherit = 'purchase.request'

    @api.depends('subcon_production_id', 'is_a_subcontracting')
    def _compute_production_name(self):
        for record in self:
            name = ''
            production_id = record.subcon_production_id
            if record.is_a_subcontracting and production_id:
                name = '%s - %s' % (production_id.name, production_id.product_id.name)
            record.subcon_production_name = name

    is_a_subcontracting = fields.Boolean(string='Is a Subcontracting')
    subcon_production_id = fields.Many2one('mrp.production', string='ProductionOrder')
    subcon_production_name = fields.Char(string='Production Order Name', compute=_compute_production_name, store=True)
    subcon_product_qty = fields.Float(string='Subcontract Quantity', digits='Product Unit of Measure')
    subcon_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    subcon_requisition_id = fields.Many2one('purchase.requisition', string='Blanket Order')

