# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

TIME_MODE_ORDER = [
    ('create_time', 'Base on Order Create Time'),
    ('update_time', 'Base on Order Update Time')
]


class WizardMPOrder(models.TransientModel):
    _name = 'wiz.mp.order'
    _description = 'Wizard Marketplace Order'

    PARAMS = [
        ('by_date_range', 'By Date Range'),
        ('by_mp_invoice_number', 'By MP Invoice Number'),
    ]

    INTERVAL_TYPES = [
        ('days', 'Day(s)'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
    ]

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="MP Account", required=True)
    marketplace = fields.Selection(related="mp_account_id.marketplace", string="Marketplace")
    params = fields.Selection(string="Parameter", selection=PARAMS, required=True, default="by_date_range")
    use_interval = fields.Boolean(string="Use Interval?", default=True)
    interval = fields.Integer(string="Interval", required=False, default=3)
    interval_type = fields.Selection(string="Interval Type", selection=INTERVAL_TYPES, required=False, default="days")
    from_date = fields.Datetime(string="From Date", required=False)
    to_date = fields.Datetime(string="To Date", required=False)
    mp_invoice_number = fields.Char(string="MP Invoice Number", required=False)
    range_type = fields.Selection(string="Time Mode", selection=TIME_MODE_ORDER, default='update_time')

    @api.onchange('interval', 'interval_type')
    def onchange_interval(self):
        interval = dict([(self.interval_type, self.interval)])
        time_delta = relativedelta(**interval)
        now = fields.Datetime.from_string(fields.Datetime.now())
        self.from_date = fields.Datetime.to_string(now - time_delta)
        self.to_date = fields.Datetime.to_string(now)

    def get_order(self):
        kwargs = {'params': self.params,
                  'force_update': self._context.get('force_update', False),
                  'time_mode': self.range_type}
        if self.params == 'by_date_range':
            from_date = fields.Datetime.from_string(self.from_date)
            to_date = fields.Datetime.from_string(self.to_date)
            if from_date > to_date:
                raise ValidationError(
                    "Invalid date range, from_date higher than to_date. Please input correct date range!")
            kwargs.update({'from_date': from_date, 'to_date': to_date})
        elif self.params == 'by_mp_invoice_number':
            kwargs.update({'mp_invoice_number': self.mp_invoice_number})
        if hasattr(self.mp_account_id, '%s_get_orders' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_orders' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
