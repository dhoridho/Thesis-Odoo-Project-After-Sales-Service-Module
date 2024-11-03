from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_reset_to_new(self):
        ''' Reset the move to the 'draft' state. '''
        if self.state != 'posted':
            raise UserError(_("Only posted moves can be reset to draft."))
        self.write({'state': 'draft'})
        return True
    
    @api.model_create_multi
    def create(self, data_list):

        for data in data_list:
            data['company_id'] = self.env.company.id
            # data['state'] = 'draft'
        return super(AccountMove, self).create(data_list)
    

    @api.model
    def _create(self, data_list):
        records = super(AccountMove, self)._create(data_list)
        for record in records:
            record.company_id = self.env.company.id
            # record.state = 'draft'

        return records 
    
    