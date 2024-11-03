# See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountTaxReport(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'sg.account.tax.report'
    _description = 'Tax Report'

    def _print_report(self, data):
        return self.env.ref(
            'sg_account_report.'
            'action_report_account_tax').report_action(self, data=data)
