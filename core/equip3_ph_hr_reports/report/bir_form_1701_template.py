import time

from odoo import api, models


class BirForm1701Report(models.AbstractModel):
    _name = 'report.equip3_ph_hr_reports.bir_form_1701_template'
    _description = "BIR Form 1701 Report"

    def _get_report_values(self, docids, data=None):
        ctx = self.env.context
        model = ctx.get('active_model', 'bir.form.1701.wizard')
        docs = self.env[model].browse(ctx.get('active_id', docids))
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
            }
