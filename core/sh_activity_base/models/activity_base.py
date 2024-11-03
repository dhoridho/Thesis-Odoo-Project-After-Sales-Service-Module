# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import html2plaintext


class ResCompany(models.Model):
    _inherit = 'res.company'

    activity_due_notification = fields.Boolean("Due Activity Notification")
    ondue_date_notify = fields.Boolean("On Due Date")

    after_first_notify = fields.Boolean("First Days After Due Date")
    after_second_notify = fields.Boolean("Second Days After Due Date")
    before_first_notify = fields.Boolean("First Days Before Due Date")
    before_second_notify = fields.Boolean("Second Days Before Due Date")

    enter_after_first_notify = fields.Integer(
        "Enter First Days After Due Date")
    enter_after_second_notify = fields.Integer(
        "Enter Second Days After Due Date")
    enter_before_first_notify = fields.Integer(
        "Enter First Days Before Due Date")
    enter_before_second_notify = fields.Integer(
        "Enter Second Days Before Due Date")
                                            
    notify_create_user_due = fields.Boolean("Notify Create User Due")
    notify_create_user_after_first = fields.Boolean("Notify Create User After First")
    notify_create_user_after_second = fields.Boolean("Notify Create User After Second")
    notify_create_user_before_first = fields.Boolean("Notify Create User Before First")
    notify_create_user_before_second = fields.Boolean("Notify Create User Before Second")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    activity_due_notification = fields.Boolean(
        "Due Activity Notification", related='company_id.activity_due_notification', readonly=False)
    ondue_date_notify = fields.Boolean(
        "On Due Date", related='company_id.ondue_date_notify', readonly=False)

    after_first_notify = fields.Boolean(
        "First Days After Due Date", related='company_id.after_first_notify', readonly=False)
    after_second_notify = fields.Boolean(
        "Second Days After Due Date", related='company_id.after_second_notify', readonly=False)
    before_first_notify = fields.Boolean(
        "First Days Before Due Date", related='company_id.before_first_notify', readonly=False)
    before_second_notify = fields.Boolean(
        "Second Days Before Due Date", related='company_id.before_second_notify', readonly=False)

    enter_after_first_notify = fields.Integer(
        "Enter First Days After Due Date", related='company_id.enter_after_first_notify', readonly=False)
    enter_after_second_notify = fields.Integer(
        "Enter Second Days After Due Date", related='company_id.enter_after_second_notify', readonly=False)
    enter_before_first_notify = fields.Integer(
        "Enter First Days Before Due Date", related='company_id.enter_before_first_notify', readonly=False)
    enter_before_second_notify = fields.Integer(
        "Enter Second Days Before Due Date", related='company_id.enter_before_second_notify', readonly=False)

    notify_create_user_due = fields.Boolean(
        "Notify Create User", related='company_id.notify_create_user_due', readonly=False)
    notify_create_user_after_first = fields.Boolean(
        "Notify Create User After First", related='company_id.notify_create_user_after_first', readonly=False)
    notify_create_user_after_second = fields.Boolean(
        "Notify Create User After Second", related='company_id.notify_create_user_after_second', readonly=False)
    notify_create_user_before_first = fields.Boolean(
        "Notify Create User Before First", related='company_id.notify_create_user_before_first', readonly=False)
    notify_create_user_before_second = fields.Boolean(
        "Notify Create User Before Second", related='company_id.notify_create_user_before_second', readonly=False)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    text_note = fields.Char("Notes In Char format ",
                            compute='_compute_html_to_char_note')

    def _compute_html_to_char_note(self):
        if self:
            for rec in self:
                if rec.note:
                    rec.text_note = html2plaintext(rec.note)
                else:
                    rec.text_note = ''

    @api.model
    def notify_mail_activity_fun(self):

        template = self.env.ref(
            'sh_acitivity_notification.template_mail_activity_due_notify_email')
        notify_create_user_template = self.env.ref(
            'sh_acitivity_notification.template_mail_activity_due_notify_email_create_user')
        company_object = self.env['res.company'].search(
            [('activity_due_notification', '=', True)], limit=1)

        if template and company_object and company_object.activity_due_notification:

            activity_obj = self.env['mail.activity'].search([])

            if activity_obj:
                for record in activity_obj:
                    if record.date_deadline and record.user_id and record.user_id.commercial_partner_id and record.user_id.commercial_partner_id.email:

                        # On Due Date
                        if company_object.ondue_date_notify:

                            if datetime.strptime(str(record.date_deadline), DEFAULT_SERVER_DATE_FORMAT).date() == datetime.now().date():
                                template.send_mail(record.id, force_send=True)
                                if notify_create_user_template and company_object.notify_create_user_due:
                                    if record.user_id.id != record.create_uid.id:
                                        notify_create_user_template.send_mail(
                                            record.id, force_send=True)
                        # On After First Notify
                        if company_object.after_first_notify and company_object.enter_after_first_notify:
                            after_date = datetime.strptime(str(record.date_deadline), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) + timedelta(days=company_object.enter_after_first_notify)

                            if after_date == datetime.now().date():
                                template.send_mail(record.id, force_send=True)
                                if notify_create_user_template and company_object.notify_create_user_after_first:
                                    if record.user_id.id != record.create_uid.id:
                                        notify_create_user_template.send_mail(
                                            record.id, force_send=True)
                        # On After Second Notify
                        if company_object.after_second_notify and company_object.enter_after_second_notify:
                            after_date = datetime.strptime(str(record.date_deadline), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) + timedelta(days=company_object.enter_after_second_notify)

                            if after_date == datetime.now().date():
                                template.send_mail(record.id, force_send=True)
                                if notify_create_user_template and company_object.notify_create_user_after_second:
                                    if record.user_id.id != record.create_uid.id:
                                        notify_create_user_template.send_mail(
                                            record.id, force_send=True)
                        # On Before First Notify
                        if company_object.before_first_notify and company_object.enter_before_first_notify:
                            before_date = datetime.strptime(str(record.date_deadline), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) - timedelta(days=company_object.enter_before_first_notify)

                            if before_date == datetime.now().date():
                                template.send_mail(record.id, force_send=True)
                                if notify_create_user_template and company_object.notify_create_user_before_first:
                                    if record.user_id.id != record.create_uid.id:
                                        notify_create_user_template.send_mail(
                                            record.id, force_send=True)
                        # On Before Second Notify
                        if company_object.before_second_notify and company_object.enter_before_second_notify:
                            before_date = datetime.strptime(str(record.date_deadline), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) - timedelta(days=company_object.enter_before_second_notify)

                            if before_date == datetime.now().date():
                                template.send_mail(record.id, force_send=True)
                                if notify_create_user_template and company_object.notify_create_user_before_second:
                                    if record.user_id.id != record.create_uid.id:
                                        notify_create_user_template.send_mail(
                                            record.id, force_send=True)
