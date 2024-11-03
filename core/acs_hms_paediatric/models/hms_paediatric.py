    # -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models ,_
from odoo.exceptions import UserError


class AcsChartData(models.Model):
    _name = 'acs.growth.chart.data'
    _description =  'Chart Data'
    _rec_name = 'age'
    _order = 'sequence, id'

    age = fields.Float('Age')
    sequence = fields.Integer(string='Sequence', default=10)
    male_value = fields.Float(string ='Normal Male Value')
    female_value = fields.Float(string ='Normal Female Value')
    record_type = fields.Selection([
        ('weight','Weight'),
        ('height','Height'),
        ('head_circum','Head Circumference'),
        ], 'Type', default='weight')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   