from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    brand_setting = fields.Selection([('without', 'Without Brand'), ('optional', 'Optional Brand Selection'), ('mandatory', 'Mandatory Brand Selection')])


    # @api.constrains('name')
    # def _validate_name(self):
    #     company = self.env['res.company'].search([])
    #     company_firts_name = [name.split()[0].lower() for name in company.mapped('name')]
    #     first_name = self.name.split()[0].lower()
    #     company_firts_name.remove(first_name) #avoiding the current company name
    #     if first_name in company_firts_name:
    #         raise ValidationError(_('Please differentiate the first name of the company %s to avoid naming issue', first_name.upper()))
