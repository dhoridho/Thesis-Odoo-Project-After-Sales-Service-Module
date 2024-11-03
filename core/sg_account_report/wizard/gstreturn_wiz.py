import time
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountGstreturn(models.TransientModel):
    _inherit = 'account.common.account.report'
    _name = 'account.gstreturn'
    _description = "Gst Return"

    date_from = fields.Date('Start Date', required=True,
                            default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(
        'End Date', required=True,
        default=lambda *a: str(
            date.today() + relativedelta(months=+1, day=1, days=-1)))
    box10 = fields.Float('Box10')
    box11 = fields.Float('Box11')
    box12 = fields.Float('Box12')

    def check_report(self):
        """Check the report."""
        datas = self.read([])[0]
        return self.env.ref(
            'sg_account_report.gst_form5_report').report_action(
                self, data=datas, config=False)
