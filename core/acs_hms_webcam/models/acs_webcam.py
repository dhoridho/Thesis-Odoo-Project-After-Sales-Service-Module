# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HmsPatient(models.Model):
    _name = 'hms.patient'
    _inherit = ['hms.patient','acs.webcam.mixin']

    def acs_webcam_retrun_action(self):
        self.ensure_one()
        return self.env.ref('acs_hms_base.action_patient').id


class HmsPhysician(models.Model):
    _name = 'hms.physician'
    _inherit = ['hms.physician','acs.webcam.mixin']

    def acs_webcam_retrun_action(self):
        self.ensure_one()
        return self.env.ref('acs_hms_base.action_physician').id

