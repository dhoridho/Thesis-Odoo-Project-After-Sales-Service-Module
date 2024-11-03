# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree

    
class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'
    
    
    def button_immediate_install(self):
        res = super(IrModuleModule, self).button_immediate_install()
        for module in self:
            if module.name == 'equip3_accounting_operation':
                equip3_accounting_operation_module = self.env['ir.module.module'].search([('name','=','equip3_accounting_operation')])
                if equip3_accounting_operation_module:
                    group_user_id = self.env.ref('base.group_user')
                    try:
                        account_staff_group = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff')
                    except:
                        account_staff_group = False
                    account_staff_id = account_staff_group and account_staff_group.id or 0
                    setting_group = self.env.ref('base.group_system')
                    billing_group = self.env.ref('account.group_account_invoice')
                    account_manager_group = self.env.ref('account.group_account_user')
                    billing_manager_group = self.env.ref('account.group_account_manager')
                    base_groups = self.env['res.groups'].browse([group_user_id.id])
                    
                    #Remove Internal Users group has inherited to Accountant Staff group
                    if account_staff_id in base_groups.implied_ids.ids:
                        base_groups.write({'implied_ids': [(3,account_staff_id)]})

                    #Remove Administration/Settings has inherited to Accountant Staff group
                    if account_staff_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,account_staff_group.id)]})
                    
                    #Remove Administration/Settings has inherited to Billing group
                    if billing_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,billing_group.id)]})
                        
                    #Remove Administration/Settings has inherited to Account Manager group
                    if account_manager_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,account_manager_group.id)]})
                        
                    #Remove Administration/Settings has inherited to Billing Manager group
                    if billing_manager_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,billing_manager_group.id)]})
        
        return res
    
    def button_immediate_upgrade(self):
        res = super(IrModuleModule, self).button_immediate_upgrade()
        for module in self:
            if module.name == 'equip3_accounting_operation':
                equip3_accounting_operation_module = self.env['ir.module.module'].search([('name','=','equip3_accounting_operation')])
                if equip3_accounting_operation_module:
                    group_user_id = self.env.ref('base.group_user')
                    try:
                        account_staff_group = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff')
                    except:
                        account_staff_group = False
                    account_staff_id = account_staff_group and account_staff_group.id or 0
                    setting_group = self.env.ref('base.group_system')
                    billing_group = self.env.ref('account.group_account_invoice')
                    account_manager_group = self.env.ref('account.group_account_user')
                    billing_manager_group = self.env.ref('account.group_account_manager')
                    base_groups = self.env['res.groups'].browse([group_user_id.id])
                    
                    #Remove Internal Users group has inherited to Accountant Staff group
                    if account_staff_id in base_groups.implied_ids.ids:
                        base_groups.write({'implied_ids': [(3,account_staff_id)]})

                    #Remove Administration/Settings has inherited to Accountant Staff group
                    if account_staff_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,account_staff_id)]})
                    
                    #Remove Administration/Settings has inherited to Billing group
                    if billing_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,billing_group.id)]})
                        
                    #Remove Administration/Settings has inherited to Account Manager group
                    if account_manager_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,account_manager_group.id)]})
                        
                    #Remove Administration/Settings has inherited to Billing Manager group
                    if billing_manager_group.id in setting_group.implied_ids.ids:
                        setting_group.write({'implied_ids': [(3,billing_manager_group.id)]})
        
        return res
