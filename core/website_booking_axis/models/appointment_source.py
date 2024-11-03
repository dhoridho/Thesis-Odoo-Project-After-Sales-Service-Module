# -*- coding: utf-8 -*-

from odoo import models, fields, api


class appointment_source(models.Model):
    _name = 'appointment.source'
    _description = 'appointment_source'

    name = fields.Char(string='Source',required=True)