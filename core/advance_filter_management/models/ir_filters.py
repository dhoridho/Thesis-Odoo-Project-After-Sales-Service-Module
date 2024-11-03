from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import ast
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

def context_today():
    return datetime.today()

class IrFilters(models.Model):
    _inherit = "ir.filters"

    models_id=fields.Many2one('ir.model', string='Model')
    model_name = fields.Char(string='Model Name', related='models_id.model', store=True)
    selection=fields.Selection([('filter','Filter'),('group_by','Group By')],default='filter')
    fields_id= fields.Many2one('ir.model.fields',string="Field")
    user_ids = fields.Many2many('res.users', 'filters_filters_users_rel_ah', 'f_id', 'user_id',
                                'Users' ,default=lambda self: self.env.user) 
    custom = fields.Boolean("Custom")
    is_readonly_data = fields.Boolean("Read Data", compute='_compute_is_readonly_data' ,default=False)

   
    @api.depends('user_ids')
    def _compute_is_readonly_data(self):
        for record in self:
            is_readonly_data = False
            if self.env.user.has_group('advance_filter_management.group_filters_admin'):
                is_readonly_data = False
            elif self.env.user.has_group('advance_filter_management.group_filters_user'): 
                if len(record.user_ids) > 1 or self.env.user not in record.user_ids._origin :
                    is_readonly_data = True
            record.is_readonly_data = is_readonly_data
            
            
    @api.onchange('user_ids')
    def _onchange_user(self):
        if self.env.user._origin.has_group('advance_filter_management.group_filters_admin'):
            self.write({'user_ids': self.user_ids._origin})
        else :
            self.write({'user_ids': self.env.user._origin})
            
    @api.onchange('fields_id')
    def _context_onchange(self):
        if self.fields_id:
            context="{'group_by':['%s']}"%self.fields_id.name
            self.context=context
    @api.model
    def get_filters(self, model, action_id=None):
        data =super(IrFilters, self).get_filters(model, action_id=action_id)
        prepare_data=[]
        uid = self.env.user.id
        for data_dic in data:
            if data_dic.get('domain'):
                try:
                    domain=eval(data_dic['domain'])
                except:
                    raise ValidationError('Please change format domain correctly : '+str(data_dic['domain']))
                if isinstance(domain, list):
                    for dom in domain:
                        if dom[0] not in ['|', '&']:
                            field_name=dom[0]
                            operator_value=dom[1]
                            value=dom[2]

                            left_value_split_list = field_name.split('.')
                            model_string = model
                            left_user = False
                            left_company = False
                            for field in left_value_split_list:
                                left_user = False
                                left_company = False
                                model_obj = self.env[model_string]
                                field_type = model_obj.fields_get()[field]['type']
                                if field_type in ['many2one', 'many2many', 'one2many']:
                                    field_relation = model_obj.fields_get()[field]['relation']
                                    model_string = field_relation
                                    if model_string == 'res.users':
                                        left_user = True
                                    if model_string == 'res.company':
                                        left_company = True
                                if left_user:
                                    if operator_value in ['in', 'not in']:
                                        if isinstance(value, list) and 0 in value:
                                            zero_index = value.index(0)
                                            value[zero_index] = self.env.user.id

                                if left_company:
                                    if operator_value in ['in', 'not in']:
                                        if isinstance(value, list) and 0 in value:
                                            zero_index = value.index(0)
                                            value[zero_index] = self.env.company.id
                
                data_dic['domain']=str(domain)
                prepare_data.append(data_dic)
        return prepare_data
        
   
