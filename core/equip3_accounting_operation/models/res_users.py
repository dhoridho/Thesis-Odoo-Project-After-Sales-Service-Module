# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree

    
class ResUsers(models.Model):
    _inherit = 'res.users'
    
    
    # @api.model
    # def default_get(self, field):
    #     res = super(ResUsers, self).default_get(field)
    #     setting_group = self.env.ref('base.group_system')
    #     access_right_group = self.env.ref('base.group_erp_manager')
        
    #     account_manager_group = self.env.ref('account.group_account_user')
    #     billing_manager_group = self.env.ref('account.group_account_manager')
    #     billing_group = self.env.ref('account.group_account_invoice')
        
    #     if res.get('groups_id'):
    #         groups_id = res.get('groups_id')
    #         if groups_id[0][0] == 6:
    #             new_groups_id =  groups_id[0][2]
                
    #             if setting_group.id in new_groups_id:
    #                 new_groups_id.remove(setting_group.id)
                
    #             if access_right_group.id in new_groups_id:
    #                 new_groups_id.remove(access_right_group.id)
                 
                
    #             if account_manager_group.id in new_groups_id:
    #                 new_groups_id.remove(account_manager_group.id)
                    
    #             if billing_manager_group.id in new_groups_id:
    #                 new_groups_id.remove(billing_manager_group.id)
                
    #             if billing_group.id in new_groups_id:
    #                 new_groups_id.remove(billing_group.id)
                    
    #             try:
    #                 account_staff_group = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff')
    #             except:
    #                 account_staff_group = False
                    
    #             if account_staff_group:
    #                 if account_staff_group.id in new_groups_id:
    #                     new_groups_id.remove(account_staff_group.id)

    #             res['groups_id'] = [(6,0,new_groups_id)]
                
    #     return res
    
    # @api.model
    # def create(self, vals):
    #     res = super(ResUsers, self).create(vals)
    #     equip3_accounting_operation_module = self.env['ir.module.module'].search([('name','=','equip3_accounting_operation'),('state','=','installed')])
    #     if equip3_accounting_operation_module:
    #         group_user_id = self.env.ref('base.group_user')
    #         try:
    #             account_staff_group = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff')
    #         except:
    #             account_staff_group = False
    #         account_staff_id = account_staff_group and account_staff_group.id or 0
    #         if group_user_id:
    #             base_groups = self.env['res.groups'].browse([group_user_id.id])
    #             if account_staff_id in base_groups.implied_ids.ids:
    #                 base_groups.write({'implied_ids': [(3,account_staff_id)]})
    #     return res
    
    
    # def write(self, vals):
    #     res = super(ResUsers, self).write(vals)
    #     equip3_accounting_operation_module = self.env['ir.module.module'].search([('name','=','equip3_accounting_operation'),('state','=','installed')])
    #     if equip3_accounting_operation_module:
    #         group_user_id = self.env.ref('base.group_user')
    #         try:
    #             account_staff_group = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff')
    #         except:
    #             account_staff_group = False
    #         account_staff_id = account_staff_group and account_staff_group.id or 0
    #         if group_user_id:
    #             base_groups = self.env['res.groups'].browse([group_user_id.id])
    #             if account_staff_id in base_groups.implied_ids.ids:
    #                 base_groups.write({'implied_ids': [(3,account_staff_id)]})
    #     return res