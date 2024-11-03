from numpy import append
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    group_id = fields.Many2one('account.analytic.group', string='Analytic Category', check_company=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name, company_id)', 'The name of the analytic tag must be unique!')
    ]

    # @api.constrains('name')
    # def _check_name(self):
    #     for record in self:
    #         # Check if the name is 'New'
    #         if record.name == 'New':
    #             raise ValidationError("Name cannot be 'New'")
    #         # Check for duplicate names
    #         duplicate = self.search([('name', '=', record.name), ('company_id', '!=', record.company_id.id), ('id', '!=', record.id)])
    #         if duplicate:
    #             raise ValidationError("The name of the analytic tag must be unique")
     
    def name_get(self):
        record = super ().name_get()
        if not self.env.context.get('show_only_name'):
            return record
        new_names = []
        for record in self: 
            name = record.name
            new_names.append((record.id, name))
        return new_names
    
    @api.model
    def create(self,values):
        record = super (AccountAnalyticAccount, self).create(values)
        for records in record :
            self.env['account.analytic.new'].with_context(skip_create=True).create({'name' : record.id, 'group_id' : record.group_id.id})
        return records
