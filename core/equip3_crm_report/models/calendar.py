# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    meeting_count = fields.Integer(string='Meeting Count', compute='_compute_event_count', store=True)
    duration_count = fields.Float(string='Duration Count', compute='_compute_event_count', store=True)
    reschedule_count = fields.Integer(string='Rescheduled (Count)', compute='_compute_event_count', store=True)
    done_count = fields.Integer(string='Done (Count)', compute='_compute_event_count', store=True)
    cancel_count = fields.Integer(string='Cancelled (Count)', compute='_compute_event_count', store=True)

    @api.depends('state', 'start', 'user_id')
    def _compute_event_count(self):
        for record in self:
            meeting_ids = self.search([
                        ('user_id', '!=', False),
                        ('user_id', '=', record.user_id.id),
                        ('start', '=', record.start)
                    ])
            done_meeting_ids = meeting_ids.filtered(lambda r: r.state in ('meeting', 'done'))
            record.meeting_count = len(done_meeting_ids)
            record.duration_count = sum(done_meeting_ids.mapped('duration'))
            record.reschedule_count = len(meeting_ids.filtered(lambda r: r.state == 'rescheduled'))
            record.done_count = len(meeting_ids.filtered(lambda r: r.state == 'done'))
            record.cancel_count = len(meeting_ids.filtered(lambda r: r.state == 'cancel'))

    @api.model
    def create(self, vals):
        res = super(CalendarEvent, self).create(vals)
        first_meeting_date = False
        second_meeting_date = False
        if res.opportunity_id:
            fts_meeting_days = 0
            cts_meeting_days = 0

            lead_data = res.env['calendar.event'].search([('opportunity_id', '=', res.opportunity_id.id)],
                                                          order='id asc', limit=2)
            if lead_data:
                rec_cnt = 1
                for lead_rec in lead_data:
                    if rec_cnt == 1:
                        first_meeting_date = lead_rec.start
                        rec_cnt = 2
                    else:
                        second_meeting_date = lead_rec.start

                if second_meeting_date:
                    cts_meeting_days = (second_meeting_date - res.opportunity_id.create_date).days
                    fts_meeting_days = (second_meeting_date-first_meeting_date).days

                    res.opportunity_id.write({
                        'first_to_second_meeting_days': fts_meeting_days,
                        'created_to_second_meeting_days': cts_meeting_days
                    })

            diff = (res.start - res.opportunity_id.create_date)
            days = diff.days
            sec = diff.seconds
            hour = days * 24 + sec // 3600
            if not res.opportunity_id.meeting_date and not res.opportunity_id.meeting_day:
                res.opportunity_id.write({
                    'meeting_date': res.start,
                    'meeting_day': hour,
                 })
            else:
                if res.opportunity_id.meeting_date > res.start:
                    res.opportunity_id.write({
                        'meeting_date': res.start,
                        'meeting_day': hour,
                    })
        return res

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            return self
        res = super(CalendarEvent, self).write(vals)
        first_meeting_date = False
        second_meeting_date = False
        if self.opportunity_id:
            fts_meeting_days = 0
            cts_meeting_days = 0
            lead_data = self.env['calendar.event'].search([('opportunity_id', '=', self.opportunity_id.id)],
                                                          order='id asc', limit=2)
            if lead_data:
                rec_cnt = 1
                for lead_rec in lead_data:
                    if rec_cnt == 1:
                        first_meeting_date = lead_rec.start
                        rec_cnt = 2
                    else:
                        second_meeting_date = lead_rec.start

                if second_meeting_date:
                    cts_meeting_days = (second_meeting_date - self.opportunity_id.create_date).days
                    fts_meeting_days = (second_meeting_date-first_meeting_date).days

                    self.opportunity_id.write({
                        'first_to_second_meeting_days': fts_meeting_days,
                        'created_to_second_meeting_days': cts_meeting_days
                    })

        if self.opportunity_id and 'start' in vals:
            diff = (self.start - self.opportunity_id.create_date)
            days = diff.days
            sec = diff.seconds
            hour = days * 24 + sec // 3600
            self.opportunity_id.write({
                'meeting_date': self.start,
                'meeting_day': hour,
            })
        return res