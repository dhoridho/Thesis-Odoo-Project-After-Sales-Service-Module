import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models


class ReportDocumentExpire(models.AbstractModel):
    _name = 'report.sg_document_expiry.document_expirey_report'
    _description = "Document Expire Report"

    def _get_report_values(self, docids, data=None):
        next_date = datetime.today().date() + relativedelta(months=1)
        immig_obj = self.env['employee.immigration']
        immigration_rec = immig_obj.search([
            ('exp_date', '=', next_date)], order='employee_id desc')
        return {
            'doc_model': immig_obj,
            'data': data,
            'docs': immigration_rec,
            'time': time,
            'documents': immigration_rec,
        }
