# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError

class MealType(models.Model):
    _name = 'meals.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Name", tracking=True)
    delivery_time = fields.Float("Delivery Time", tracking=True, help="The time at which meals will be delivered")
    created_date = fields.Date("Creation Date", default=fields.Date.today, readonly=True, tracking=True)
    created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.uid, readonly=True, tracking=True)

    @api.constrains('delivery_time')
    def check_date(self):
        for rec in self:
            if rec.delivery_time < 1.0:
                raise ValidationError("Delivery time can only be filled starting from 01:00 o'clock")
            elif  rec.delivery_time >= 24.0:
                raise ValidationError("Delivery time can only be filled maximum 23.59 o'clock")
            
    @api.constrains('name')
    def check_name(self):
        for nama in self:
            namas = self.search([('name','=',nama.name),('id','!=',nama.id)])
            if len(namas)>=1:
                raise ValidationError("Name must be unique")
