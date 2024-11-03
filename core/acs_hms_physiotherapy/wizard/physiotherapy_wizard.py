# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _

class SendtoPhysiotherapy(models.TransientModel):
    _name = 'physiotherapy.send'
    _description = 'Send to Physiotherapy'

    grp_exercise_ids = fields.One2many('physiotherapy.exercise.lines','wiz_id',string='Exercise')


    def send_to_physiotherapy(self):
        res = {}
        record_id = self.env.context and self.env.context.get('active_id', False) or False
        appointment = self.env['hms.appointment'].browse(record_id)
        exercise_lines = []
        for ex in self.grp_exercise_ids:
            exercise_lines.append((0, 0, {
                'group_id': ex.group_id.id, 
                'price': ex.price,
                'exercise_ids': [(6,0,ex.exercise_ids.ids)]
            }))
        self.env['acs.physiotherapy'].create({
            'appointment_id': appointment.id,
            'patient_id': appointment.patient_id.id,
            'grp_exercise_ids': exercise_lines
        })
        return res


class PhysiotherapyExerciseLines(models.TransientModel):
    _name = "physiotherapy.exercise.lines"
    _description = 'Physiotherapy Exercise Lines'
    
    group_id = fields.Many2one('physiotherapy.exercise.group','Exercise group', required=True)
    wiz_id = fields.Many2one('physiotherapy.send','Wiz ID')
    exercise_ids = fields.Many2many('physiotherapy.exercise','rel_wizard_exercise_group_exercise_line','exercise_id','exercise_group_id',string='Exercise')
    price = fields.Float(related='group_id.product_id.list_price', string='Price',store=True)
    
    @api.onchange('group_id')
    def onchange_group_id(self):
        self.exercise_ids = self.group_id.exercise_ids
        self.price = self.group_id.product_id.list_price
