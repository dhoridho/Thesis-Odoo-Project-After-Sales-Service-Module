# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_auto_add_followers = fields.Boolean('Auto add vendors as followers ?')
    sh_portal_user_create = fields.Boolean('Auto portal users(vendors) create ?')
    sh_tender_document_manage = fields.Boolean('Manage Tender Documents ?')


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_auto_add_followers = fields.Boolean('Auto add vendors as followers ?',related = 'company_id.sh_auto_add_followers',readonly=False)
    sh_portal_user_create = fields.Boolean('Auto portal users(vendors) create ?',related = 'company_id.sh_portal_user_create',readonly=False)
    sh_tender_document_manage = fields.Boolean('Manage Tender Documents ?',related = 'company_id.sh_tender_document_manage',readonly=False)