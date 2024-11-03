# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models

class CrmLeadMeetingCancel(models.TransientModel):
    _name = 'calendar.event.reschedule.wizard'
    _description = 'Get Meeting Reschedule Reason'

    reschedule_date = fields.Datetime(string='Starting at meeting date', required=False)
    reschedule_reason = fields.Char(string='Reschedule Reasons', required=True)
    have_reschedule_date = fields.Boolean(string='Have Reschedule Date')

    def action_meeting_reschedule_apply(self):
        meetings = self.env['calendar.event'].browse(self.env.context.get('active_ids'))
        meetings.write(dict(state='rescheduled', reasons_reschedule=self.reschedule_reason))

        if self.have_reschedule_date:
            date_start = self.reschedule_date
            date_stop = self.reschedule_date + timedelta(minutes=round((meetings.duration or 1.0) * 60))

            vals = [{
                'name': meetings.name,
                'start': date_start,
                'stop': date_stop,
                'duration': meetings.duration,
                'allday': meetings.allday,
                'location': meetings.location,
                'opportunity_id': meetings.opportunity_id.id,
                'user_id': meetings.user_id.id,
                'team_id': meetings.team_id.id,
                'description': meetings.description,
                'partner_ids': [(6, 0, meetings.partner_ids.ids)],
                'categ_ids': [(6, 0, meetings.categ_ids.ids)],
                'alarm_ids': [(6, 0, meetings.alarm_ids.ids)],
                'res_model': meetings.res_model,
                'res_id': meetings.res_id,
                'res_model_id': meetings.res_model_id.id,
            }]
            self.env['calendar.event'].create(vals)
