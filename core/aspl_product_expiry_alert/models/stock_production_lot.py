# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import fields, models, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError



class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    expiry_state = fields.Selection([('expired', 'Expired'), ('near_expired', 'Near Expired')], string="State", compute='_get_production_lot_state')
    state_check = fields.Selection([('Expired', 'Expired'), ('Near Expired', 'Near Expired')], string="Expiry State")
    product_expiry_reminder = fields.Boolean(compute='_compute_product_expiry_reminder', help="The Expiration Date has been reached.")

    @api.depends('alert_date')
    def _compute_product_expiry_reminder(self):
        current_date = fields.Datetime.now()
        for lot in self:
            if lot.alert_date and not lot.product_expiry_alert:
                lot.product_expiry_reminder = lot.alert_date <= current_date
            else:
                lot. product_expiry_reminder = False


    # @api.constrains('alert_date', 'expiration_date')
    # def _check_dates(self):
    #     for each in self: 
    #         if each.alert_date and each.expiration_date and each.alert_date > each.expiration_date:
    #             raise ValidationError(_('Dates must be: Alert Date < Expiry Date'))

    # @api.model
    # def name_search(self, name, args=None, operator='=', limit=100):
    #     if self._context.get('default_product_id'):
    #         stock_production_lot_obj = self.env['stock.production.lot']
    #         args = args or []
    #         recs = self.search([('product_id', '=', self._context.get('default_product_id'))])
    #         if recs:
    #             for each_stock_lot in recs.filtered(lambda l: l.expiration_date).sorted(key=lambda p: (p.expiration_date),
    #                                                                               reverse=False):
    #                 if each_stock_lot.expiry_state != 'expired':
    #                     stock_production_lot_obj |= each_stock_lot
    #             return stock_production_lot_obj.name_get()
    #     return super(StockProductionLot, self).name_search(name, args, operator, limit)

    @api.model
    def product_state_check(self):
        today_date = date.today()
        for each_stock_lot in self.filtered(lambda l: l.expiration_date):
            if each_stock_lot.product_id.tracking != 'none':
                expiration_date = datetime.strptime(str(each_stock_lot.expiration_date), '%Y-%m-%d %H:%M:%S').date()
                if expiration_date < today_date:
                    each_stock_lot.write({'state_check': 'expired'})
                else:
                    if each_stock_lot.alert_date:
                        alert_date = datetime.strptime(str(each_stock_lot.alert_date), '%Y-%m-%d %H:%M:%S').date()
                        if alert_date <= today_date:
                            each_stock_lot.write({'state_check': 'near_expired'})
            else:
                each_stock_lot.write({'state_check': ''})

    @api.depends('alert_date', 'expiration_date')
    def _get_production_lot_state(self):
        today_date = date.today()
        for each_stock_lot in self:
            each_stock_lot.expiry_state = ''
            each_stock_lot.state_check = ''
            if each_stock_lot.product_expiry_alert:
                each_stock_lot.expiry_state = 'expired'
                each_stock_lot.state_check = 'Expired'
            if each_stock_lot.product_expiry_reminder:
                each_stock_lot.expiry_state = 'near_expired'
                each_stock_lot.state_check = 'Near Expired'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: