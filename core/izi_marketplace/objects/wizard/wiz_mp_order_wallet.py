# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class WizardMPOrdersWallet(models.TransientModel):
    _name = 'wiz.mp.order.wallet'
    _description = 'Wizard Marketplace Orders Wallet'

    PARAMS = [
        ('by_date_range', 'By Date Range'),
    ]

    INTERVAL_TYPES = [
        ('days', 'Day(s)'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
    ]

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="MP Account", required=True)
    params = fields.Selection(string="Parameter", selection=PARAMS, required=True, default="by_date_range")
    use_interval = fields.Boolean(string="Use Interval?", default=True)
    interval = fields.Integer(string="Interval", required=False, default=3)
    interval_type = fields.Selection(string="Interval Type", selection=INTERVAL_TYPES, required=False, default="days")
    from_date = fields.Datetime(string="From Date", required=False)
    to_date = fields.Datetime(string="To Date", required=False)
    # auto_reconcile = fields.Boolean(string="Automatic Reconcile ?")
    mode = fields.Selection([
        ("data_only", "Get Data Only"),
        ("reconcile_only", "Reconcile Only"),
        ("both", ("Get Data and Reconcile"))], string='Wallet Mode', default='data_only')

    @api.onchange('interval', 'interval_type')
    def onchange_interval(self):
        interval = dict([(self.interval_type, self.interval)])
        time_delta = relativedelta(**interval)
        now = fields.Date.from_string(fields.Datetime.today())
        self.from_date = fields.Date.to_string(now - time_delta)
        self.to_date = fields.Date.to_string(now)

    def get_orders_wallet(self):
        bank_statement = False
        if not self.mp_account_id.wallet_journal_id:
            raise ValidationError('Account Jurnal For this marketpalce not to set ! please set first.')
        kwargs = {'params': self.params,
                  'force_update': self._context.get('force_update', False)}
        if self.params == 'by_date_range':
            from_date = fields.Datetime.from_string(self.from_date)
            to_date = fields.Datetime.from_string(self.to_date)
            if from_date > to_date:
                raise ValidationError(
                    "Invalid date range, from_date higher than to_date. Please input correct date range!")
            kwargs.update({'from_date': from_date, 'to_date': to_date, 'mode': self.mode})
        if hasattr(self.mp_account_id, '%s_get_orders_wallet' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_orders_wallet' % self.mp_account_id.marketplace)(**kwargs)

        # if self.auto_reconcile:
        #     if bank_statement:
        #         bank_statement_list = [data['name'] for data in bank_statement]
        #         kwargs.update({'bank_statement_list': bank_statement_list})
        #     if hasattr(self.mp_account_id, '%s_auto_reconcile' % self.mp_account_id.marketplace):
        #         getattr(self.mp_account_id, '%s_auto_reconcile' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'force_show_number': 1
            }
        }
