from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class CashAdvanceResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_advance_approval_matrix = fields.Boolean(config_parameter='equip3_hr_cash_advance.cash_advance_approval_matrix', default=False)
    cash_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')], default='employee_hierarchy',
        config_parameter='equip3_hr_cash_advance.cash_type_approval')
    cash_level = fields.Integer(config_parameter='equip3_hr_cash_advance.cash_level', default=1)
    send_by_wa_cashadvance = fields.Boolean(config_parameter='equip3_hr_cash_advance.send_by_wa_cashadvance')
    send_by_email_cashadvance = fields.Boolean(config_parameter='equip3_hr_cash_advance.send_by_email_cashadvance', default=True)
    #Auto Email Follow Cron
    auto_follow_up_cash = fields.Boolean(config_parameter='equip3_hr_cash_advance.auto_follow_up_cash')
    interval_number_cash = fields.Integer(config_parameter='equip3_hr_cash_advance.interval_number_cash')
    interval_type_cash = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
        default='',
        config_parameter='equip3_hr_cash_advance.interval_type_cash')
    number_of_repititions_cash = fields.Integer(
        config_parameter='equip3_hr_cash_advance.number_of_repititions_cash')
    deposit_reconcile_journal_id = fields.Many2one('account.journal', string="Reconcile Journal", company_dependent=True, related='company_id.deposit_reconcile_journal_id', readonly=False,)
    journal_id = fields.Many2one('account.journal', string="Payment Method", company_dependent=True, related='company_id.journal_id', readonly=False)
    deposit_account_id = fields.Many2one('account.account', string="Advance Account", company_dependent=True, related='company_id.deposit_account_id', readonly=False)

    @api.model
    def default_get(self, rec):
        res = super(CashAdvanceResConfigSettings, self).default_get(rec)
        company = self.env.company
        res.update({
            'deposit_reconcile_journal_id': company.deposit_reconcile_journal_id,
            'deposit_account_id': company.deposit_account_id,
            'journal_id': company.journal_id
        })
        return res

    def _update_ca_multi_cmp(self):
        if self.deposit_reconcile_journal_id:
            self.company_id.sudo().update({'deposit_reconcile_journal_id': self.deposit_reconcile_journal_id})
        if self.journal_id:
            self.company_id.sudo().update({'journal_id': self.journal_id})
        if self.deposit_account_id:
            self.company_id.sudo().update({'deposit_account_id': self.deposit_account_id})

    @api.onchange("cash_level")
    def _onchange_cash_level(self):
        if self.cash_level < 1:
            self.cash_level = 1

    @api.onchange("interval_number_cash")
    def _onchange_interval_number_cash(self):
        if self.interval_number_cash < 1:
            self.interval_number_cash = 1

    @api.onchange("number_of_repititions_cash")
    def _onchange_number_of_repititions_cash(self):
        if self.number_of_repititions_cash < 1:
            self.number_of_repititions_cash = 1

    def set_values(self):
        super(CashAdvanceResConfigSettings,self).set_values()
        self._update_ca_multi_cmp()
        cron_cash_approver = self.env['ir.cron'].sudo().search([('name', '=', 'Auto Follow Up Cash Approver')])
        if self.auto_follow_up_cash == True :
            if cron_cash_approver:
                interval = self.interval_number_cash
                delta_var = self.interval_type_cash
                delta_var = 'month' if delta_var == 'months' else delta_var
                if delta_var and interval:
                    next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
                cron_cash_approver.write({'interval_number':self.interval_number_cash,'interval_type':self.interval_type_cash,'nextcall':next_call,'active':True})
        else:
            if cron_cash_approver:
                cron_cash_approver.write({'active':False})

    def execute(self):
        if not self.deposit_account_id or not self.deposit_reconcile_journal_id:
            raise UserError("Please fill in the mandatory fields in Reconcile Journal and Advance Account")

        return super(CashAdvanceResConfigSettings, self).execute()