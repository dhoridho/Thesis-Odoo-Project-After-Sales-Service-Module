
import time
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class Gstf7(models.TransientModel):
    _inherit = 'account.common.account.report'
    _name = 'account.gstreturnf7'
    _description = "Gst F7 Return"

    date_from = fields.Date('Start Date',
                            required=True,
                            default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(
        'End Date', required=True,
        default=lambda *a: str(date.today() + relativedelta(
            months=+1, day=1, days=-1)))
    net_gst_prevs = fields.Float('Net GST paid previously',
                                 help='Net GST paid previously for this \
                                 accounting period.')
    box10 = fields.Float('Box10')
    box11 = fields.Float('Box11')
    box12 = fields.Float('Box12')
    notes = fields.Text('Notes')

    def check_report(self):
        """Check report."""
        datas = self.read([])[0]
        report_id = self.env.ref('sg_account_report.gst_form7_report')
        return report_id.report_action(self, data=datas, config=False)
