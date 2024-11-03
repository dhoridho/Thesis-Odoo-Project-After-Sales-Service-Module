from odoo import api, models, _


class TrialBalance(models.AbstractModel):
    _inherit = 'report.dynamic_accounts_report.trial_balance'

    @api.model
    def _get_report_values(self, docids, data=None):
        result = super(TrialBalance, self)._get_report_values(docids, data=data)
        if self.env.context.get('trial_pdf_report'):

            if data.get('report_data'):
                result.update({'opening_debit_total': data.get('report_data')['opening_debit_total'],
                               'opening_credit_total': data.get('report_data')['opening_credit_total'],
                               'ending_debit_total': data.get('report_data')['ending_debit_total'],
                               'ending_credit_total': data.get('report_data')['ending_credit_total'],
                               'ending_balance_total': data.get('report_data')['ending_balance_total'],
                               'ending_balance_debit_total': data.get('report_data')['ending_balance_debit_total'],
                               'ending_balance_credit_total': data.get('report_data')['ending_balance_credit_total'],
                               })
        return result

    def get_filter(self, option):
        res = super(TrialBalance, self).get_filter(option)
        res['company_id'] = self.env.company
        return res
