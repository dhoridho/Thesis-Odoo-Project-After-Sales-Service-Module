# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountingBudgetConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    accounting_budget_use_theoretical_achievement = fields.Boolean(string="Use Theoretical Amount and Achievement", config_parameter='equip3_accounting_budget.accounting_budget_use_theoretical_achievement')
    is_purchase_request_overbudget_approval_matrix = fields.Boolean(string="Purchase Request Overbudget Approval Matrix")
    is_purchase_order_overbudget_approval_matrix = fields.Boolean(string="Purchase Order Overbudget Approval Matrix")
    is_allow_purchase_budget = fields.Boolean(string="Allow Purchase Budget", default=False)
    is_wa_notification_budget = fields.Boolean(string="Enable Whatsapp Notification", config_parameter='is_wa_notification_budget')

    @api.onchange('is_budget_approval_matrix')
    def onchange_is_budget_approval_matrix(self):
        if not self.is_budget_approval_matrix:
            self.is_wa_notification_budget = False

    
    @api.onchange('group_om_account_budget')
    def onchange_for_accounting_budget_use_theoretical_achievement(self):
        if not self.group_om_account_budget:
            self.accounting_budget_use_theoretical_achievement = False

    @api.onchange('is_allow_purchase_budget')
    def onchange_is_allow_purchase_budget(self):
        if not self.is_allow_purchase_budget:
            self.is_purchase_request_overbudget_approval_matrix = False
            self.is_purchase_order_overbudget_approval_matrix = False

    @api.model
    def get_values(self):
        res = super(AccountingBudgetConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_purchase_request_overbudget_approval_matrix': IrConfigParam.get_param('is_purchase_request_overbudget_approval_matrix', False),
            'is_purchase_order_overbudget_approval_matrix': IrConfigParam.get_param('is_purchase_order_overbudget_approval_matrix', False),
            'is_allow_purchase_budget': IrConfigParam.get_param('is_allow_purchase_budget', False),
        })
        return res

    def set_values(self):
        if self.purchase == False:
            self.update({
                'is_purchase_request_overbudget_approval_matrix': False,
                'is_purchase_order_overbudget_approval_matrix': False,
                'is_allow_purchase_budget': False,
            })
        super(AccountingBudgetConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_request_overbudget_approval_matrix', self.is_purchase_request_overbudget_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_order_overbudget_approval_matrix', self.is_purchase_order_overbudget_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_allow_purchase_budget', self.is_allow_purchase_budget)