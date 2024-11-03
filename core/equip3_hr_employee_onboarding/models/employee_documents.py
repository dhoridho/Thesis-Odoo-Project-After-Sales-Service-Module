# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployeeDocument(models.Model):
    _inherit = 'hr.employee.document'

    onboarding_id = fields.Many2one('employee.orientation', string="Employee Onboarding")
    offboarding_id = fields.Many2one('employee.offboarding', string="Employee Offboarding")
    checklist_document_id = fields.Many2one('employee.checklists', string="Checklist Document")