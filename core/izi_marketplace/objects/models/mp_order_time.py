# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MarketplaceOrderTime(models.Model):
    _name = 'mp.order.time'
    _description = 'Marketplace Order Time'

    name = fields.Char('Name')
    mp_account_ids = fields.Many2many('mp.account', string='Marketplace Accounts')
    line_ids = fields.One2many('mp.order.time.line', 'mp_order_time_id', 'List Of Working Day')
    day_off_ids = fields.One2many('mp.order.day.off', 'mp_order_time_id', 'List of Day Off')
    active = fields.Boolean('Active', default=True)


class MarketplaceOrderTimeLine(models.Model):
    _name = 'mp.order.time.line'
    _description = 'Marketplace Order Time Line'
    _sql_constraints = [
        ('unique_order_day', 'UNIQUE(mp_order_time_id,day)', 'Day is Duplicated!')
    ]

    _DAY_SELECTION = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ]

    name = fields.Char('Name', compute='_get_day', store=True)
    mp_order_time_id = fields.Many2one('mp.order.time')
    day = fields.Selection(selection=_DAY_SELECTION, string='Day')
    cutoff_time = fields.Float(string='Cutoff Time')

    @api.depends('name', 'day')
    def _get_day(self):
        for rec in self:
            if rec.day:
                rec.name = rec.day
            else:
                rec.name = ''


class MarketplaceOrderDayOff(models.Model):
    _name = 'mp.order.day.off'
    _description = 'Marketplace Order Day Off'

    name = fields.Char('Reason Day Off')
    mp_order_time_id = fields.Many2one('mp.order.time')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    @api.onchange('start_date', 'end_date')
    def validasi_form(self):
        # Validasi rentan waktu pada field 'date_start' dan 'date_end'
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                return {
                    'warning': {
                        'title': 'Interval Warning',
                        'message': 'Date end must be higher from date start',
                    }
                }
