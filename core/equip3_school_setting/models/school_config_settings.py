# -*- coding: utf-8 -*-
from odoo import models, fields


class SchoolConfigSettings(models.Model):
    _name = "school.config.settings"
    _description = "School Config Settings"

    name = fields.Char(string="Name")
    leave_approval_matrix = fields.Boolean(string="Leave Approval Matrix")
    student_leave_request_per_subject = fields.Boolean(
        string="Student Leave Request Per Subject"
    )
