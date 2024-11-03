# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class ActitivyAlarm(models.Model):
    _name = "sh.activity.alarm"
    _description = "Alarm Reminder"

    name = fields.Char(string="Name", readonly=True)
    type = fields.Selection([('email', 'Email'), (
        'popup', 'Popup')], string="Type", required=True, default='email')
    sh_remind_before = fields.Integer(
        string="Reminder Before")
    sh_reminder_unit = fields.Selection([('Hour(s)', 'Hour(s)'), (
        'Minute(s)', 'Minute(s)'), ('Second(s)', 'Second(s)')], string="Reminder Unit", default='Hour(s)',required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    
    @api.constrains('sh_remind_before')
    def _check_sh_currency_rate(self):
        if self.filtered(lambda c: c.sh_reminder_unit == 'Minute(s)' and c.sh_remind_before < 5):
            raise ValidationError(_("Reminder Before can't set less than 5 Minutes."))
        elif self.filtered(lambda c: c.sh_reminder_unit == 'Second(s)' and c.sh_remind_before < 300):
            raise ValidationError(_("Reminder Before can't set less than 300 Seconds."))
        elif self.filtered(lambda c: c.sh_reminder_unit == 'Hour(s)' and c.sh_remind_before < 1):
            raise ValidationError(_("Reminder Before can't set less than 1 Hour."))
    
    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.browse(self.ids).read(['sh_remind_before', 'sh_reminder_unit','type'])
        return [(alarm.id, '%s%s%s' % (str(alarm.sh_remind_before)+' ',str(alarm.sh_reminder_unit)+' ','['+str(alarm.type)+']'))
                for alarm in self]
    
    @api.onchange('sh_remind_before','type','sh_reminder_unit')
    def _onchange_name(self):
        for rec in self:
            rec.name = rec.name_get()[0][1]
    
    @api.model
    def _run_activity_reminder(self):
        if self.env.company.sh_display_activity_reminder:
            alarm_ids = self.env['sh.activity.alarm'].sudo().search([])
            if alarm_ids:
                for alarm in alarm_ids:
                    activity_ids = self.env['mail.activity'].sudo().search([('sh_activity_alarm_ids','in',[alarm.id])])
                    if activity_ids:
                        for activity in activity_ids:
                            deadline_date = False
                            if alarm.sh_reminder_unit == 'Hour(s)' and activity.sh_date_deadline:
                                deadline_date_hours_added = activity.sh_date_deadline + timedelta(hours = 5,minutes=30,seconds=0)
                                deadline_date = deadline_date_hours_added - timedelta(hours = alarm.sh_remind_before)
                            elif alarm.sh_reminder_unit == 'Minute(s)' and activity.sh_date_deadline:
                                deadline_date_minutes_added = activity.sh_date_deadline + timedelta(hours = 5,minutes=30,seconds=0)
                                deadline_date = deadline_date_minutes_added - timedelta(minutes = alarm.sh_remind_before)
                            elif alarm.sh_reminder_unit == 'Second(s)' and activity.sh_date_deadline:
                                deadline_date_seconds_added = activity.sh_date_deadline + timedelta(hours = 5,minutes=30,seconds=0)
                                deadline_date = deadline_date_seconds_added - timedelta(seconds = alarm.sh_remind_before)
                            if deadline_date and deadline_date != False:
                                if alarm.type == 'popup':
                                    now = fields.Datetime.now() + timedelta(hours = 5,minutes=30,seconds=0)
                                    if fields.Date.today() == deadline_date.date() and deadline_date.hour == now.hour and deadline_date.minute == now.minute:
                                        notifications = []
                                        message=""
                                        if activity.res_model_id:
                                            message+="<strong>"+str(activity.res_model_id.name) + ' : ' + "</strong>"
                                        if activity.res_name:
                                            message+=str(activity.res_name) +'</br>'
                                        if activity.date_deadline:
                                            message+='<strong>Due Date : </strong>' + str(activity.date_deadline) +'</br>'
                                        if activity.summary:
                                            message+='<strong>Summary : </strong>' + str(activity.summary) +'</br>'
                                        if activity.user_id:
                                            message+='<strong>Assigned To : </strong>' + str(activity.user_id.name) +'</br>'
                                        if activity.supervisor_id:
                                            message+='<strong>Supervisor : </strong>' + str(activity.supervisor_id.name) +'</br>'
                                        multiple_users = []
                                        if activity.sh_user_ids:
                                            for user in activity.sh_user_ids:
                                                if user.name not in multiple_users:
                                                    multiple_users.append(user.name)
                                        if len(multiple_users) > 0:
                                            message+='<strong>Assign Multi Users : </strong>'
                                            for user in multiple_users:
                                                message+='<span class="badge badge-info" style="padding-right:5px">'+str(user) +'</span>'
                                            message+='</br>'
                                        activity_tags = []
                                        if activity.sh_activity_tags:
                                            for activity_tag in activity.sh_activity_tags: 
                                                if activity_tag.name not in activity_tags:
                                                    activity_tags.append(activity_tag.name)
                                        if len(activity_tags) > 0:
                                            message+='<strong>Activity Tags : </strong>'
                                            for tag in activity_tags:
                                                message+='<span class="badge badge-info" style="padding-right:5px">'+str(tag) +'</span>'
                                            message+='</br>'
                                        activity_menu_id = self.env.ref('sh_activities_management.sh_activity_dashboard').id
                                        activity_href = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url')) + '/web#id='+str(activity.id)+'&model=mail.activity&view_type=form&menu_id='+str(activity_menu_id)
                                        model_href = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url')) + '/web#id='+str(activity.res_id)+'&model='+str(activity.res_model)+'&view_type=form'
                                        message+="<a style='color:#7C7BAD;padding-right:10px' class='btn btn-link' data-dismiss='toast'>Close</a>"
                                        message+="<a href="+str(activity_href)+" target='_blank' class='btn btn-link' style='padding-right:10px;'>Activity</a>"
                                        message+="<a href="+str(model_href)+" target='_blank' class='btn btn-link' style='padding-right:10px;'>"+str(activity.res_model_id.name)+"</a>"
                                        user_ids = []
                                        if activity.user_id:
                                            if activity.user_id.id not in user_ids:
                                                user_ids.append(activity.user_id.id)
                                        if activity.supervisor_id:
                                            if activity.supervisor_id.id not in user_ids:
                                                user_ids.append(activity.supervisor_id.id)
                                        if activity.sh_user_ids:
                                            for user in activity.sh_user_ids:
                                                if user.id not in user_ids:
                                                    user_ids.append(user.id)
                                        if len(user_ids) > 0:
                                            for user_id in user_ids:
                                                notification_user_id = self.env['res.users'].sudo().browse(user_id)
                                                if notification_user_id:
                                                    notifications.append([
                                                        (self._cr.dbname, 'res.partner', notification_user_id.partner_id.id),
                                                        {'type': 'user_connection', 'title': _('Activity Reminder '+'('+str(activity.activity_type_id.name)+')'), 'message':  message, 'sticky': True, 'warning': False}  # sorted to make deterministic for tests
                                                    ])
                                        self.env['bus.bus'].sendmany(notifications)
                                elif alarm.type == 'email':
                                    now = fields.Datetime.now() + timedelta(hours = 5,minutes=30,seconds=0)
                                    if fields.Date.today() == deadline_date.date() and deadline_date.hour == now.hour and deadline_date.minute == now.minute:
                                        reminder_template = self.env.ref('sh_activities_management.sh_activity_reminder_mail_template')
                                        partner_ids = []
                                        if activity.user_id:
                                            if activity.user_id.partner_id.id not in partner_ids:
                                                partner_ids.append(str(activity.user_id.partner_id.id))
                                        if activity.supervisor_id:
                                            if activity.supervisor_id.partner_id.id not in partner_ids:
                                                partner_ids.append(str(activity.supervisor_id.partner_id.id))
                                        if activity.sh_user_ids:
                                            for user in activity.sh_user_ids:
                                                if user.partner_id.id not in partner_ids:
                                                    partner_ids.append(str(user.partner_id.id))
                                        if len(partner_ids) > 0:
                                            partner_ids = ','.join(partner_ids)
                                            if reminder_template and partner_ids:
                                                reminder_template.sudo().write({
                                                    'partner_to': partner_ids
                                                })
                                                reminder_template.sudo().send_mail(activity.id, force_send=True,
                                                                                     notif_layout='mail.mail_notification_light')
                                