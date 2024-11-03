# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AcsJitsiMeet(models.Model):
    _inherit = 'acs.video.call'

    appointment_id = fields.Many2one('hms.appointment', string='Appointment', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: