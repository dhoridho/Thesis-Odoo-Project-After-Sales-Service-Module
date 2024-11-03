# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, date, timedelta

class AcsHospitalization(models.Model):
    _inherit = "acs.hospitalization"

    def _rec_count(self):
        rec = super(AcsHospitalization, self)._rec_count()
        for rec in self:
            rec.ot_booking_count = len(rec.ot_booking_ids.ids)

    ot_booking_ids = fields.One2many('acs.ot.booking', 'hospitalization_id', string='OT Bookings')
    ot_booking_count = fields.Integer(compute='_rec_count', string='# OT Bookings')

    def action_ot_booking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_operation_theater.action_acs_ot_booking")
        action['domain'] = [('hospitalization_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.patient_id.id,
            'default_hospitalization_id': self.id}
        return action
