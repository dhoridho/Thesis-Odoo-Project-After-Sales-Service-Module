# -*- coding: utf-8 -*-
from geopy import distance
from odoo import api, fields, models, _


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    active_location = fields.Many2one('res.partner', string="Active Location")

    def attendance_location(self, next_action, latitude=None, longitude=None, entered_pin=None):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        att_range = int(self.env.user.partner_id.attendance_range)
        if latitude is not None and longitude is not None:
            act_latitude = self.sudo().active_location.partner_latitude
            act_longitude = self.active_location.partner_longitude
            if act_latitude and act_longitude:
                pdistance = distance.distance((act_latitude, act_longitude), (latitude, longitude)).km
                if (pdistance*1000) <= att_range:
                    return self.attendance_manual(next_action=next_action, entered_pin=entered_pin)
                else:
                    return {'warning': _("You can only do check in/out within Active Location range")}
        return self.attendance_manual(next_action=next_action, entered_pin=entered_pin)
