from odoo import api , fields , models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hse_operation = fields.Boolean(string="Health Safety Environment") 

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_hse_action_approval_matrix = fields.Boolean(string="Action Checklist Approval Matrix")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_hse_action_approval_matrix = IrConfigParam.get_param('is_hse_action_approval_matrix')
        if is_hse_action_approval_matrix is None:
            is_hse_action_approval_matrix = True
        res.update({
            'is_hse_action_approval_matrix': is_hse_action_approval_matrix,
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('is_hse_action_approval_matrix', self.is_hse_action_approval_matrix)



