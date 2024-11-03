# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import json
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.release import version


class Appointment(models.Model):
    _inherit = 'hms.appointment'

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    @api.depends('patient_id','patient_id.birthday','date')
    def _get_age_months(self):
        for rec in self:
            if rec.patient_id.birthday:
                delta = relativedelta(rec.date, rec.patient_id.birthday)
                rec.age_month = (delta.years*12) + delta.months

    height = fields.Float(string='Height', help="Height of Child", states=READONLY_STATES)
    head_circum = fields.Float('Head Circumference', states=READONLY_STATES)
    is_child = fields.Boolean(related="patient_id.is_child", string="Is Child")
    age_month = fields.Float(compute="_get_age_months", string='Age(Months)', store=True)


class ACSPatient (models.Model):
    _inherit = "hms.patient"

    def get_line_graph_datas(self, record_type):
        if record_type=='height':
            rec_name = 'Height'
            child_value = self.birth_height
        if record_type=='weight':
            rec_name = 'Weight'
            child_value = self.birth_weight
        if record_type=='head_circum':
            rec_name = 'Head Circumference'
            child_value = self.birth_head_circum

        normal_data = []
        child_data = []
        normal_record_datas = self.env['acs.growth.chart.data'].search([('record_type','=',record_type)])

        for normal_record_data in normal_record_datas:
            #Value based on gender
            normal_record_data_value = normal_record_data.male_value if self.gender=='male' else normal_record_data.female_value
            normal_data.append({'x': normal_record_data.age, 'y':normal_record_data_value, 'name': 'Normal %s' % rec_name})
            child_record_data = self.env['hms.appointment'].search([('patient_id','=',self.id), ('age_month','=',int(normal_record_data.age))], limit=1)
            if child_record_data:
                if record_type=='height' and child_record_data.height:
                    child_value = child_record_data.height
                if record_type=='weight' and child_record_data.weight:
                    child_value = child_record_data.weight
                if record_type=='head_circum' and child_record_data.head_circum:
                    child_value = child_record_data.head_circum
            child_data.append({'x': normal_record_data.age, 'y':child_value, 'name': 'Child %s' % rec_name})

        [normal_graph_title, normal_graph_key] = ['Normal %s Growth Chart' % rec_name, _('Normal %s Growth Chart' % rec_name)]
        [child_graph_title, child_graph_key] = ['Child %s Growth Chart' % rec_name, _('Child %s Growth Chart' % rec_name)]
        
        normal_color = '#875A7B' if '+e' in version else '#7c7bad'
        child_color = 'green'

        return [
            {'values': normal_data, 'title': normal_graph_title, 'key': normal_graph_key, 'area': False, 'color': normal_color},
            {'values': child_data, 'title': child_graph_title, 'key': child_graph_key, 'area': False, 'color': child_color}
        ]

    def _compute_dashboard_data(self):
        self.patient_height_growth = json.dumps(self.get_line_graph_datas(record_type='height'))
        self.patient_weight_growth = json.dumps(self.get_line_graph_datas(record_type='weight'))
        self.patient_head_circum_graph = json.dumps(self.get_line_graph_datas(record_type='head_circum'))

    is_child = fields.Boolean("Is Child")
    birth_weight = fields.Float(string='Birth Weight', help="Weight of Child")
    birth_height = fields.Float(string='Birth Height', help="Height of Child")
    birth_head_circum = fields.Float('Birth Head Circumference')

    patient_height_growth = fields.Text(compute='_compute_dashboard_data')
    patient_weight_growth = fields.Text(compute='_compute_dashboard_data')
    patient_head_circum_graph = fields.Text(compute='_compute_dashboard_data')


    def show_growth_chart(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_paediatric.action_growth_chart")
        action['domain'] = [('id', '=', self.id)]
        return action


class HrDepartment(models.Model): 
    _inherit = "hr.department"

    department_type = fields.Selection(selection_add=[('paediatric','Paediatric')])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: