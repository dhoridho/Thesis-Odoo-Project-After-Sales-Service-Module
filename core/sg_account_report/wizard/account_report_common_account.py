# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountCommonAccountReport(models.TransientModel):
    _name = 'account.common.account.report'
    _description = 'Account Common Account Report'
    _inherit = "account.common.report"

    display_account = fields.Selection(
        [('all', 'All'),
         ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0'), ],
        string='Display Accounts', required=True, default='movement')

    is_ytd = fields.Boolean("Display YTD Amounts?")

    def pre_print_report(self, data):
        """Print the report."""
        data['form'].update(self.read(['display_account', 'is_ytd'])[0])
        return data
