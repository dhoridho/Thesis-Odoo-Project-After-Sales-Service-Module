# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_range = fields.Integer(string='Attendance Range')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['attendance_range'] = int(self.env['ir.config_parameter'].sudo().get_param('hr_attendance_location_knk.attendance_range', default=50))
        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('hr_attendance_location_knk.attendance_range', self.attendance_range)
        super(ResConfigSettings, self).set_values()
