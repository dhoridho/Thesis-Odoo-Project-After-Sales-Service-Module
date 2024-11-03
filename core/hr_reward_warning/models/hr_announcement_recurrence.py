# -*- coding: utf-8 -*-
from datetime import datetime, time, date
import pytz

from odoo import api, fields, models, _

class AnnouncementRecurrenceRule(models.Model):
    _name = 'hr.announcement.recurrence'
    _description = 'Announcement Recurrence Rule'

    announcement_id = fields.Many2one(
        'hr.announcement', ondelete='set null', copy=False)
    recurrence_date_start = fields.Date(string='Recurrence Start Date')
    recurrence_date_end = fields.Date(string='Recurrence End Date')
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('expired', 'Expired')],
                             string='Status', default='draft')

    def action_cron_recurrent(self):
        announce = self.env['hr.announcement'].search([('state', '=', 'expired')])
        for res in announce:
            if res.recurrency:
                now_date = date.today()
                recurrence_ids = res.recurrence_ids
                for rec in recurrence_ids:
                    if rec.state == 'draft' and rec.recurrence_date_start >= now_date and now_date <= rec.recurrence_date_start:
                        rec.write({
                            'state': 'running'
                        })
                        res.write({
                            'date_start': rec.recurrence_date_start,
                            'date_end': rec.recurrence_date_end,
                            'state': 'submitted'
                        })
                    elif rec.state == 'running' and rec.recurrence_date_end < now_date:
                        rec.write({
                            'state': 'expired'
                        })
