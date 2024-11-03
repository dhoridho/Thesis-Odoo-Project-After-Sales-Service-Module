from odoo import api, fields, models, _
class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def action_rejected_customer(self):
        for record in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'approval.matrix.customer.reject',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }