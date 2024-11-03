from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cr_expiry_date = fields.Integer(string="Claim Request Expiry Date")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'cr_expiry_date': IrConfigParam.get_param('cr_expiry_date', '1'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('cr_expiry_date', self.cr_expiry_date) 
        if self.is_claim_request_approval_matrix:
            self.env.ref('equip3_construction_accounting_operation.approving_matrix_claim_request').active = True
            self.env.ref('equip3_construction_accounting_operation.approving_matrix_claim_request_vendor').active = True
        else:
            self.env.ref('equip3_construction_accounting_operation.approving_matrix_claim_request').active = False
            self.env.ref('equip3_construction_accounting_operation.approving_matrix_claim_request_vendor').active = True