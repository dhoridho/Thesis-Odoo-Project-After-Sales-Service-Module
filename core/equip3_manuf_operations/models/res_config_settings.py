from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_plan_order_creation = fields.Selection(selection=[
        ('auto_po_allow_manual', 'Automatic Creation of Production Order and Allow Manual Creation'),
        ('manual_po_allow_auto', 'Manual Creation of Production Order and Allow Automatic Creation'),
        ('auto_po_prohibit_manual', 'Automatic Creation of Production Order, while Prohibiting Manual Creation'),
        ('manual_po_prohibit_auto', 'Manual Creation of Production Order, while Prohibiting Automatic Creation'),
    ], default='auto_po_allow_manual', string='Production Order Creation', config_parameter='equip3_manuf_operations.mrp_plan_order_creation')
