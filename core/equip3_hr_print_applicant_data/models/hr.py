# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################

from random import randint

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.exceptions import UserError

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Good'),
    ('2', 'Very Good'),
    ('3', 'Excellent')
]

class Applicant(models.Model):
    _inherit = "hr.applicant"

    hr_merge_pdf_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachment Merge",
        relation="rel_hr_merge_attachment_id")

    def print_applicantdata(self):
        temp = self.env.ref('equip3_hr_print_applicant_data.report_hr_applicantdata').report_action(self)
        return temp
        # return self.env.ref('equip3_hr_print_applicant_data.report_hr_applicantdata').report_action(self)