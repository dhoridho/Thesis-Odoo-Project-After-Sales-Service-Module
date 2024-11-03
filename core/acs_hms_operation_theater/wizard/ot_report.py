# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, date

class SurgeryReport(models.TransientModel):
    _name = 'hms.surgery.report'
    _description = 'Surgery Report'

    start_date = fields.Date('Start Date', required=True, default=fields.Date.today())
    end_date = fields.Date('End Date', required=True, default=fields.Date.today())
    ot_id = fields.Many2one('acs.hospital.ot','Operation Theater', required=True)

    def print_report(self):
        datas = {'ids': [self.id]}
        res = self.read([])
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('acs_hms_operation_theater.action_report_acs_hms_surgery').report_action([], data=datas)
