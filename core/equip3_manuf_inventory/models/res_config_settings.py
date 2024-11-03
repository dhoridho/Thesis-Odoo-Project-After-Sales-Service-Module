from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_use_secret_product = fields.Boolean(
        string='Use Secret Product?', 
        implied_group='equip3_manuf_inventory.group_use_secret_product')
    group_use_secret_bom = fields.Boolean(
        string='Use Secret BoM?', 
        implied_group='equip3_manuf_inventory.group_use_secret_bom')

    #  Production Plan
    mrp_allow_submit_mr_pp = fields.Boolean(
        string='MRP Allow Submit Material Request on Production Plan', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_mr_pp')
    mrp_allow_submit_it_pp = fields.Boolean(
        string='MRP Allow Submit Transfer Request on Production Plan', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_it_pp')
    mrp_allow_submit_mr_partial_pp = fields.Boolean(
        string='MRP Allow Submit Material Request Partial on Production Plan', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_mr_partial_pp')
    mrp_allow_submit_it_partial_pp = fields.Boolean(
        string='MRP Allow Submit Transfer Request Partial on Production Plan', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_it_partial_pp')
    mrp_allow_submit_it_partial_not_empty_pp = fields.Boolean(
        string='MRP Allow Submit Transfer Request Partial Not Empty on Production Plan', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_it_partial_not_empty_pp')

    # Production Order
    mrp_allow_submit_mr_po = fields.Boolean(
        string='MRP Allow Submit Material Request on Production Order', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_mr_po')
    mrp_allow_submit_it_po = fields.Boolean(
        string='MRP Allow Submit Transfer Request on Production Order', 
        config_parameter='equip3_manuf_inventory.mrp_allow_submit_it_po')

    @api.onchange('manufacturing')
    def _onchange_manufacturing_set_sercret(self):
        if not self.manufacturing:
            self.group_use_secret_product = False
            self.group_use_secret_bom = False

    @api.onchange('mrp_allow_submit_it_pp')
    def _onchange_mrp_allow_submit_it_pp(self):
        if not self.mrp_allow_submit_it_pp:
            self.mrp_allow_submit_it_partial_pp = False

    @api.onchange('mrp_allow_submit_it_partial_pp')
    def _onchange_mrp_allow_submit_it_partial_pp(self):
        if not self.mrp_allow_submit_it_partial_pp:
            self.mrp_allow_submit_it_partial_not_empty_pp = False
