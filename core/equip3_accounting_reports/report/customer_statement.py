from odoo import api, models, _


class CustomerStatementReport(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.customer_statement'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('customer_statement_pdf_report'):
            if data.get('report_data'):
                data.update({
                    'partner_data': data.get('report_data'),
                    'company_id': self.env.company.id,
                    'company_name': self.env.company.name
                })
        return data
