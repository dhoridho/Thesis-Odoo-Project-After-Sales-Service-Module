# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class MarkAsDone(models.TransientModel):
    _name = 'sh.mark.as.done'
    _description = 'Mark As Done'

    feedback = fields.Text("Feedback",required=True)
    
    def action_done(self):
        active_ids = self.env.context.get('active_ids')
        activity_ids = self.env['mail.activity'].sudo().browse(active_ids)
        if activity_ids:
            for activity_id in activity_ids:
                activity_id.state='done'
                activity_id.active=False
                activity_id.date_done = fields.Date.today()
                activity_id.feedback = self.feedback
                activity_id.activity_done = True
                activity_id._compute_state()
                messages = self.env['mail.message']
                record = self.env[activity_id.res_model].sudo().browse(activity_id.res_id)
                record.sudo().message_post_with_view(
                    'mail.message_activity_done',
                    values={
                        'activity': activity_id,
                        'feedback': self.feedback,
                        'display_assignee': activity_id.user_id != self.env.user
                    },
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_activities'),
                    mail_activity_type_id=activity_id.activity_type_id.id,
                )
                messages |= record.sudo().message_ids[0]