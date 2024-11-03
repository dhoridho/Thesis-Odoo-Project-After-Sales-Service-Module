from odoo import models, api
from datetime import datetime, timedelta
import re


class GravioLog(models.Model):
    _inherit = 'gravio.log'

    @api.model
    def sync_pos_order_logs(self):
        orders = self.env['pos.order'].search([])
        logs = self.search([])

        for order in orders:
            best_delta = timedelta.max
            best_log = self.env['gravio.log']
            for log in logs:
                delta = abs(datetime.fromtimestamp(int(log.timestamp)) - order.date_order)
                if delta < best_delta:
                    best_delta = delta
                    best_log = log

            values = {'gravio_log_id': best_log.id}
            for age in ['adult', 'child']:
                for gender in ['male', 'female']:
                    count = 0
                    match = re.search(age.title() + ' ' + gender.title() + '\:\s*\[(.*?)\]', best_log.log or '')
                    if match:
                        count = match.group(1)
                    try:
                        count = int(count)
                    except ValueError:
                        count = 0
                    values['log_%s_%s_count' % (age, gender)] = count
            order.write(values)
