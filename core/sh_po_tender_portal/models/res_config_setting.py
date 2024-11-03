# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    sh_manage_tender_doc_portal = fields.Boolean('Manage Portal Tender Document ?')


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_manage_tender_doc_portal = fields.Boolean('Manage Portal Tender Document ?',related='company_id.sh_manage_tender_doc_portal',readonly=False)