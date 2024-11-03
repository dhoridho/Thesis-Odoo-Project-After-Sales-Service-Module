from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning


class AgreementStage(models.Model):
    _inherit = 'agreement.stage'
    
    def unlink(self):
        if self.name in ['Active', 'Expired']:
            raise Warning(_("'Active' and 'Expired' stages cannot be deleted"))
        agreement = self.env['agreement'].search([('stage_id', '=', self.id)])
        if agreement:
            raise Warning(_("Contracts are in this stage. You cannot delete this stage"))
        return super(AgreementStage, self).unlink()