# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_expiry_notification = fields.Boolean("Expiry Notification")
    sh_is_notify_vendor = fields.Boolean("Notify Vendor")
    sh_on_date_notify = fields.Boolean("On Date Notification")
    enter_before_first_notify = fields.Integer(
        "Notify Before Expiry Date")
    enter_before_second_notify = fields.Integer(
        "Notify Before Expiry Date")
    enter_before_third_notify = fields.Integer(
        "Notify Before Expiry Date")
    enter_after_first_notify = fields.Integer(
        "Notify After Expiry Date")
    enter_after_second_notify = fields.Integer(
        "Notify After Expiry Date")
    enter_after_third_notify = fields.Integer(
        "Notify After Expiry Date")
    attachment_email = fields.Char("Email to")

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_expiry_notification = fields.Boolean(
        string="Expiry Notification", related='company_id.sh_expiry_notification', readonly=False)
    sh_is_notify_vendor = fields.Boolean(
        string="Notify Vendor", related='company_id.sh_is_notify_vendor', readonly=False)
    sh_on_date_notify = fields.Boolean(
        string="On Date Notification", related='company_id.sh_on_date_notify', readonly=False)
    enter_before_first_notify = fields.Integer(
        "Notify Before Expiry Date", related='company_id.enter_before_first_notify', readonly=False)
    enter_before_second_notify = fields.Integer(
        "Notify Before Expiry Date", related='company_id.enter_before_second_notify', readonly=False)
    enter_before_third_notify = fields.Integer(
        string="Notify Before Expiry Date", related='company_id.enter_before_third_notify', readonly=False)
    enter_after_first_notify = fields.Integer(
        string="Notify After Expiry Date", related='company_id.enter_after_first_notify', readonly=False)
    enter_after_second_notify = fields.Integer(
        string="Notify After Expiry Date", related='company_id.enter_after_second_notify', readonly=False)
    enter_after_third_notify = fields.Integer(
        string="Notify After Expiry Date", related='company_id.enter_after_third_notify', readonly=False)
    attachment_email = fields.Char(string="Email to", related='company_id.attachment_email', readonly=False)
