from odoo import api, models, _


class TaxReport(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.tax_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('tax_pdf_report'):
            if data.get('report_data'):
                report_lines = data.get('report_data')['report_lines']
                record_lines = report_lines[0]['record_lines']
                currency_position = record_lines[0]['currency_position']
                currency_symbol = record_lines[0]['currency_symbol']
                data.update({'report_lines': data.get('report_data')['report_lines'],
                             'Filters': data.get('report_data')['filters'],
                             'company': self.env.company,
                             'currency_position': currency_position,
                             'currency_symbol':currency_symbol,
                             })
        return data