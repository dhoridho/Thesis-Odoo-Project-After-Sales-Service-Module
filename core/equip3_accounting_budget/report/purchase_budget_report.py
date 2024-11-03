from odoo import api, models, _


class PurchaseBudgetReport(models.AbstractModel):
    _name = 'report.equip3_accounting_budget.purchase_budget_report'
    _description = 'Purchase Budget Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if data.get('report_data'):
            data.update({
                'account_data': data.get('report_data')['report_lines'],
                'Filters': data.get('report_data')['filters'],
                'company': self.env.company,
            })
        return data