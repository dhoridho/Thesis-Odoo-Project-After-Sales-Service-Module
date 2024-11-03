from odoo import api, fields, models, _

class AccountAnalyticNew(models.Model):
    _name = 'account.analytic.new'
    _description = "Account Analytic New"

    name = fields.Many2one('account.analytic.account', string='Analytic Account', index=True, tracking=True)
    group_id = fields.Many2one('account.analytic.group',string='Analytic Group',)

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)
    
    @api.model
    def create(self,values):
        record = super (AccountAnalyticNew, self).create(values)
        if self.env.context.get('skip_create'):
            return record
        for records in record :
            record.name.group_id = record.group_id.id
        return records