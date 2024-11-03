from odoo import api, models, _


class EquityMove(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.equity_move'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('equity_move_pdf_report'):

            if data.get('report_data'):
                data.update({'account_data': data.get('report_data')['report_lines'],
                             'Filters': data.get('report_data')['filters'],
                             'debit_total': data.get('report_data')['debit_total'],
                             'credit_total': data.get('report_data')['credit_total'],
                             'balance_total': data.get('report_data')['balance_total'],
                             'company': self.env.company,
                             'account_equity_filtered': data.get('report_data')['account_equity_filtered'],
                             'account_equity': data.get('report_data')['account_equity'],
                             'account_retained_earnings': data.get('report_data')['account_retained_earnings'],
                             'account_current_earnings': data.get('report_data')['account_current_earnings'],
                             'account_prive': data.get('report_data')['account_prive'],
                             })
        return data
