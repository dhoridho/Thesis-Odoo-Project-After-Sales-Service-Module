from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    #  Production Plan
    mrp_allow_submit_pr_pp = fields.Boolean(
        string='MRP Allow Submit Purchase Request on Production Plan', 
        config_parameter='equip3_manuf_purchase.mrp_allow_submit_pr_pp')
    mrp_allow_submit_pr_partial_pp = fields.Boolean(
        string='MRP Allow Submit Partial Purchase Request on Production Plan', 
        config_parameter='equip3_manuf_purchase.mrp_allow_submit_pr_partial_pp')

    # Production Order
    mrp_allow_submit_pr_po = fields.Boolean(
        string='MRP Allow Submit Purchase Request on Production Order', 
        config_parameter='equip3_manuf_purchase.mrp_allow_submit_pr_po')

    @api.onchange('mrp_allow_submit_pr_pp')
    def _onchange_mrp_allow_submit_pr_pp(self):
        if not self.mrp_allow_submit_pr_pp:
            self.mrp_allow_submit_pr_partial_pp = False
