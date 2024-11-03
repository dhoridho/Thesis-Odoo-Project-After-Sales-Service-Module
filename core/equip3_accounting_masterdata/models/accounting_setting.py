from odoo import api , fields , models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    accounting = fields.Boolean(string="Accounting")

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_om_account_budget = fields.Boolean(string="Budget Management", 
        implied_group='equip3_accounting_masterdata.group_om_account_budget')
    credit_note_expiry_date  = fields.Boolean(string="Credit note expiry date")

    @api.onchange('group_om_account_budget')
    def _onchange_group_analytic_tags(self):
        for res in self:
            if res.group_om_account_budget:
                res.group_analytic_tags = True
                res.group_analytic_accounting = False
                
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        credit_note_expiry_date = ICPSudo.get_param('equip3_accounting_masterdata.credit_note_expiry_date')
        res.update(credit_note_expiry_date=credit_note_expiry_date)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        for rec in self:
            ICPSudo = rec.env['ir.config_parameter'].sudo()
            ICPSudo.set_param('equip3_accounting_masterdata.credit_note_expiry_date',rec.credit_note_expiry_date)