from odoo import models, fields, api, _


class MRPProduction(models.Model):
    _inherit = "mrp.production"

    @api.model
    def _default_mrp_allow_submit_pr(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_purchase.mrp_allow_submit_pr_po', 'False'))

    mrp_allow_submit_pr = fields.Boolean(string='Allow Submit Purchase Request', default=_default_mrp_allow_submit_pr)

    mrp_material_purchase_ids = fields.Many2many(
        'mrp.material.purchase', 
        'mrp_production_ids', 
        string='Material to Purchases')

    is_purchase_requested = fields.Boolean()
