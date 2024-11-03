# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAgedTrialBalance(models.TransientModel):

    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)',
                                   required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    partner_ids = fields.Many2many('res.partner', 'aged_partners', 'cust_id',
                                   'customer_id', 'Customers', required=True)

    # @api.onchange('result_selection')
    # def result_selection_onchange(self):
    #     """Based on the onchage give the result."""
    #     domain = {}
    #     partners = self.env['res.partner'].search([])
    #     self.partner_ids = False
    #     if self.result_selection == 'customer':
    #         partners = self.env['res.partner'].search(
    #             [('customer', '=', True)])
    #         domain = {'partner_ids': [('id', 'in', partners.ids)]}
    #     elif self.result_selection == 'supplier':
    #         partners = self.env['res.partner'].search(
    #             [('supplier', '=', True)])
    #         domain = {'partner_ids': [('id', 'in', partners.ids)]}
    #     elif self.result_selection == 'customer_supplier':
    #         partners = self.env['res.partner'].search(
    #             ['|', ('customer', '=', True), ('supplier', '=', True)])
    #         domain = {'partner_ids': [('id', 'in', partners.ids)]}
    #     else:
    #         domain = {'partner_ids': [('id', 'not in', partners.ids)]}
    #     return {'domain': domain}

    def _print_report(self, data):
        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length', 'partner_ids'])[0])
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))
        start_dates = data['form']['date_from'].strftime("%Y-%m-%d")
        data['form'].update({'date_from': start_dates})
        data.update({'date_from': start_dates})
        start = datetime.strptime(start_dates, "%Y-%m-%d")
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and
                         (str((5 - (i + 1)) * period_length) +
                          '-' + str((5 - i) * period_length)) or
                         ('+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        return self.env.ref(
            'sg_account_report.'
            'action_report_aged_partner_balance_v12').with_context(
                landscape=True).report_action(self, data=data)
