from odoo import api, models, _
import datetime
import time
from dateutil.relativedelta import relativedelta

class PettyCashAnalysisReport(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.pettycash_analysis'
    _description = 'Petty Cash Analysis Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('petty_cash_pdf_report'):
            if data.get('report_data'):
                last_month = datetime.date.today().replace(day=1) - relativedelta(days=1)
                get_firts_day = last_month.replace(day=1)
                data.update({'account_data': data.get('report_data')['report_lines'],
                             'Filters': data.get('report_data')['filters'],
                             'date_from': get_firts_day.strftime('%d/%m/%Y'),
                             'date_to': last_month.strftime('%d/%m/%Y'),
                             'company': self.env.company,
                             })
        return data