# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ShIrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _description = 'Ir attachment'

    expiry_date = fields.Date(required=False, default=lambda self: self._context.get(
        'Expiry Date', fields.Date.context_today(self)))

    datas_pdf = fields.Binary(related='datas')
    sh_is_notify = fields.Boolean("Expiry Date Notify ??")

    partner = fields.Many2one("res.partner", "Partner")
    email = fields.Char("Email")

    @api.model
    def notify_purchase_document_expiry(self):

        template = self.env.ref(
            'sh_all_in_one_purchase_tools.sh_purchase_document_expiry_notify_email')
        notify_create_user_template = self.env.ref(
            'sh_all_in_one_purchase_tools.sh_purchase_document_expiry_notify_email_to_user')
        company_object = self.env['res.company'].search(
            [('sh_expiry_notification', '=', True)], limit=1)

        if template and company_object and company_object.sh_expiry_notification:
            document_obj = self.env['ir.attachment'].search(
                [('res_model', '=', 'purchase.order')])
            if document_obj:
                for record in document_obj:

                    purchase_order = self.env['purchase.order'].browse(record.res_id)
                    record.write({

                        'partner': purchase_order.partner_id,
                        'email': record.company_id.attachment_email,

                    })

                    if record.expiry_date and record.sh_is_notify and record.partner:

                        # On Expiry Date
                        if company_object.sh_on_date_notify:

                            if datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date() == datetime.now().date():

                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date Before First Notify
                        if company_object.enter_before_first_notify:

                            before_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) - timedelta(days=company_object.enter_before_first_notify)
                            if before_date == datetime.now().date():

                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date Before Second Notify
                        if company_object.enter_before_second_notify:

                            before_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) - timedelta(days=company_object.enter_before_second_notify)

                            if before_date == datetime.now().date():
                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date Before Third Notify
                        if company_object.enter_before_third_notify:

                            before_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) - timedelta(days=company_object.enter_before_third_notify)

                            if before_date == datetime.now().date():
                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date After First Notify
                        if company_object.enter_after_first_notify:

                            after_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) + timedelta(days=company_object.enter_after_first_notify)

                            if after_date == datetime.now().date():
                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date After Second Notify
                        if company_object.enter_after_second_notify:

                            after_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) + timedelta(days=company_object.enter_after_second_notify)

                            if after_date == datetime.now().date():
                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)

                        # Expiry Date After Third Notify
                        if company_object.enter_after_third_notify:

                            after_date = datetime.strptime(str(record.expiry_date), DEFAULT_SERVER_DATE_FORMAT).date(
                            ) + timedelta(days=company_object.enter_after_third_notify)

                            if after_date == datetime.now().date():
                                if template and company_object.sh_is_notify_vendor:
                                    template.send_mail(
                                        record.id, force_send=True)

                                if notify_create_user_template and record.company_id.attachment_email:
                                    notify_create_user_template.send_mail(
                                        record.id, force_send=True)
