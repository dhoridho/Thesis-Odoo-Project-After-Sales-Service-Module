# -*- coding: utf-8 -*-

from odoo import models, fields


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    is_check_in_pos = fields.Boolean(string="Check IN from POS")
