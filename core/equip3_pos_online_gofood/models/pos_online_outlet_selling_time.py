# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

class PosOnlineOutletSellingTime(models.Model):
    _inherit = "pos.online.outlet.selling.time"

    def get_selling_time(self, type=None):
        self.ensure_one()
        OnlineOutlet = self.env['pos.online.outlet']
        time = self
        selling_time = {}
        if type == 'gofood':
            selling_time = {
                "monday": [],
                "tuesday": [],
                "wednesday": [],
                "thursday": [],
                "friday": [],
                "saturday": [],
                "sunday": []
            }
            
            if time.monday:
                selling_time['monday'] = [{
                    "start": OnlineOutlet.format24hour(time.monday_start_time),
                    "end": OnlineOutlet.format24hour(time.monday_end_time)
                }]

            if time.tuesday:
                selling_time['tuesday'] = [{
                    "start": OnlineOutlet.format24hour(time.tuesday_start_time),
                    "end": OnlineOutlet.format24hour(time.tuesday_end_time)
                }]

            if time.wednesday:
                selling_time['wednesday'] = [{
                    "start": OnlineOutlet.format24hour(time.wednesday_start_time),
                    "end": OnlineOutlet.format24hour(time.wednesday_end_time)
                }]

            if time.thursday:
                selling_time['thursday'] = [{
                    "start": OnlineOutlet.format24hour(time.thursday_start_time),
                    "end": OnlineOutlet.format24hour(time.thursday_end_time)
                }]

            if time.friday:
                selling_time['friday'] = [{
                    "start": OnlineOutlet.format24hour(time.friday_start_time),
                    "end": OnlineOutlet.format24hour(time.friday_end_time)
                }]

            if time.saturday:
                selling_time['saturday'] = [{
                    "start": OnlineOutlet.format24hour(time.saturday_start_time),
                    "end": OnlineOutlet.format24hour(time.saturday_end_time)
                }]

            if time.sunday:
                selling_time['sunday'] = [{
                    "start": OnlineOutlet.format24hour(time.sunday_start_time),
                    "end": OnlineOutlet.format24hour(time.sunday_end_time)
                }]
                
        return selling_time