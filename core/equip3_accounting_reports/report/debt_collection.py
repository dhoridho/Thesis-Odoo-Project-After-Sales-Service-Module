from odoo import api, models, _


class DebtCollection(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.debt_collection'
    _description = 'Debt Collection Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('trial_pdf_report'):
            if data.get('report_data'):
                data.update({
                    'debt_data': data.get('report_data')['report_lines'],
                    'Filters': data.get('report_data')['filters'],
                    'title': data.get('report_data')['name'],
                    'company': self.env.company,
                })

        return data