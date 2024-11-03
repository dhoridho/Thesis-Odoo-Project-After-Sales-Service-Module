from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class access_management(models.Model):
    _inherit = 'access.management'

    hide_custom_filter = fields.Boolean(help="The Add Custom Filter will be hidden in search view of all model from the specified users.")
    hide_custom_group = fields.Boolean(help="The Add Custom Groupby will be hidden in search view of all model from the specified users.")
    field_conditional_access_ids = fields.One2many('field.conditional.access', 'access_management_id', 'Field Conditional Access')
    
    def is_custom_filter_available(self, model):
        if self.search([('user_ids', 'in', self.env.user.id), ('company_ids', 'in', self.env.company.id), ('active', '=', True),('hide_custom_filter','=',True)]):
            return True

        if model:
            if self.env['hide.filters.groups'].search([('access_management_id.active', '=', True),
                                                 ('access_management_id.user_ids', 'in', self.env.user.id), 
                                                 ('access_management_id.company_ids', 'in', self.env.company.id),
                                                 ('model_id.model', '=', model),
                                                 ('restrict_custom_filter', '=', True)]):
                return True
        return False

    def is_custom_group_available(self, model):
        if self.search([('user_ids', 'in', self.env.user.id), ('company_ids', 'in', self.env.company.id), ('active', '=', True),('hide_custom_group','=',True)]):
            return True

        if model:
            if self.env['hide.filters.groups'].search([('access_management_id.active', '=', True),
                                                 ('access_management_id.user_ids', 'in', self.env.user.id), 
                                                 ('access_management_id.company_ids', 'in', self.env.company.id),
                                                 ('model_id.model', '=', model),
                                                 ('restrict_custom_group', '=', True)]):
                return True
        return False