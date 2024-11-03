from odoo import api, models, _

class FinancialRatioReport(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.financial_ratio_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('financial_ratio_pdf_report'):
            if data.get('report_data'):
                data.update({'Filters': data.get('report_data')['filters'],
                             'currency': data.get('report_data')['currency'],
                             'report_lines_current_ratio': data.get('report_data')['report_lines_current_ratio'],
                             'report_lines_quick_ratio': data.get('report_data')['report_lines_quick_ratio'],
                             'report_lines_capital_ratio': data.get('report_data')['report_lines_capital_ratio'],
                             'report_lines_cash_ratio': data.get('report_data')['report_lines_cash_ratio'],
                             'report_lines_debt_to_asset_ratio': data.get('report_data')['report_lines_debt_to_asset_ratio'],
                             'report_lines_debt_to_equity_ratio': data.get('report_data')['report_lines_debt_to_equity_ratio'],
                             'report_lines_long_term_debt_to_equity_ratio': data.get('report_data')['report_lines_long_term_debt_to_equity_ratio'],
                             'report_lines_times_interest_earned_ratio': data.get('report_data')['report_lines_times_interest_earned_ratio'],
                             'report_lines_EBITDA': data.get('report_data')['report_lines_EBITDA'],
                             'report_lines_return_on_asset': data.get('report_data')['report_lines_return_on_asset'],
                             'report_lines_return_on_equity': data.get('report_data')['report_lines_return_on_equity'],
                             'report_lines_profit_margin': data.get('report_data')['report_lines_profit_margin'],
                             'report_lines_gross_profit_margin': data.get('report_data')['report_lines_gross_profit_margin'],
                             'report_lines_ar_turnover_ratio': data.get('report_data')['report_lines_ar_turnover_ratio'],
                             'report_lines_merchandise_inventory': data.get('report_data')['report_lines_merchandise_inventory'],
                             'report_lines_total_assets': data.get('report_data')['report_lines_total_assets'],
                             'report_lines_net_fixed_assets': data.get('report_data')['report_lines_net_fixed_assets'],
                             'company': self.env.company,
                             })
        return data