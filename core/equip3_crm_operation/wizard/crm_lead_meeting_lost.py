# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLeadMeetingCancel(models.TransientModel):
    _name = 'calendar.event.cancel.wizard'
    _description = 'Get Meeting Cancel Reason'

    cancel_reason = fields.Text("Cancel Reason")

    def action_meeting_reason_apply(self):
        leads = self.env['calendar.event'].browse(self.env.context.get('active_ids'))
        return leads.action_set_meeting_lost(cancelled_reasons=self.cancel_reason, state='cancel')

