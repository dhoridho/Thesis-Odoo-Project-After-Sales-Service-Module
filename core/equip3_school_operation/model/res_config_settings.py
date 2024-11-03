
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    payment_instruction = fields.Binary(string="Payment Instruction")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            payment_instruction=icp.get_param("payment_instruction", False),
        )
        return res

    def set_values(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "payment_instruction", self.payment_instruction
        )
        return super(ResConfigSettings, self).set_values()
 