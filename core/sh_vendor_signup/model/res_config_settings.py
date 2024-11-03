# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models

class website(models.Model):
    _inherit = "website"

    is_enable_vendor_notification = fields.Boolean("Enable Vendor Notification")
    user_ids = fields.Many2many("res.users", string="Responsible Person")
    is_enable_auto_portal_user = fields.Boolean('Auto Portal User')
    is_enable_company_portal_user = fields.Boolean('Company ')
    is_enable_company_contact_portal_user = fields.Boolean('Contacts')

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_enable_vendor_notification = fields.Boolean(
        "Enable Vendor Notification",
        related="website_id.is_enable_vendor_notification", readonly=False)
    user_ids = fields.Many2many(
        "res.users", string="Responsible Person",
        related="website_id.user_ids", readonly=False)
    is_enable_auto_portal_user = fields.Boolean(
        'Create auto portal user vendor?',
        related="website_id.is_enable_auto_portal_user", readonly=False)

    is_enable_company_portal_user = fields.Boolean(
        'For Company ',
        related="website_id.is_enable_company_portal_user", readonly=False)
    
    is_enable_company_contact_portal_user = fields.Boolean(
        'For Contacts',
        related="website_id.is_enable_company_contact_portal_user", readonly=False)


