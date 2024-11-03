from odoo import api, fields, models, _

class AccPartner(models.Model):
    _inherit='res.partner'
    
    bank_info = fields.Char('Bank info', compute="_compute_description_name")
    
    @api.depends('bank_ids','name')
    def _compute_description_name(self):
        for partner in self:
            partner.bank_info = 'The first partner’s bank account is the default bank account'


class ResPartnerBank(models.Model):
	_inherit = "res.partner.bank"

	acc_holder_email = fields.Char('Account Holder Email')
	acc_holder_type = fields.Selection([
				        ('1', 'Personal'),
						('2', 'Corporate'),
						('3', 'Government')
				        ], string='Account Holder Type')

	acc_holder_resident = fields.Selection([
				        ('1', 'Resident'),
						('2', 'Non Resident')
				        ], string='Account Holder Resident')
	acc_holder_address = fields.Char('Account Holder Address')