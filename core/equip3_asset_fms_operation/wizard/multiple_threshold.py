# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _
from datetime import datetime,date
from odoo.exceptions import ValidationError

class MutipleThreshold(models.TransientModel):
    _name = 'multiple.threshold.wizard'
    _description = 'Add Mutiple Threshold'

    threshold_value = fields.Float(string='Threshold Value', required=True)
    start_value = fields.Float(string='Start Value', required=True)
    frequency = fields.Integer(string='Frequency', required=True)

    def add_threshold(self):
        active_id = self.env.context.get('active_id')
        start_threshold_value = self.start_value
        for freq in range(1, self.frequency+1):
            maintenance_plan_id = self.env['maintenance.plan'].search([('id', '=', active_id)])
            maintenance_plan_id.maintenance_threshold_ids = [(0,0,{
                'threshold': start_threshold_value,
                'unit': 'km' if maintenance_plan_id.is_odometer_m_plan else 'hours',
                })]
            start_threshold_value += self.threshold_value
        return True