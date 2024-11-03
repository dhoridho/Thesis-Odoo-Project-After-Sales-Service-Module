# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime, timedelta


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.depends('removal_date', 'alert_date', 'expiration_date', 'use_date')
    def _get_product_state(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.expiry_state = 'normal'
            if rec.expiration_date and rec.expiration_date < now:
                rec.expiry_state = 'expired'
            elif (rec.alert_date and rec.removal_date and
                    rec.removal_date >= now > rec.alert_date):
                rec.expiry_state = 'alert'
            elif (rec.removal_date and rec.use_date and
                    rec.use_date >= now > rec.removal_date):
                rec.expiry_state = 'to_remove'
            elif (rec.use_date and rec.expiration_date and
                    rec.expiration_date >= now > rec.use_date):
                rec.expiry_state = 'best_before'

    def _get_locked_value(self):
        return self._get_product_locked(self.product_id)

    mrp = fields.Float(string='MRP', help="If we get lot price different set this price to set invoice price")
    expiry_state = fields.Selection(
        compute=_get_product_state,
        selection=[('expired', 'Expired'),
                   ('alert', 'In alert'),
                   ('normal', 'Normal'),
                   ('to_remove', 'To remove'),
                   ('best_before', 'After the best before')],
        string='Expiry state')
    locked = fields.Boolean(string='Blocked', default='_get_locked_value', readonly=True)

    @api.onchange('expiration_date')
    def _onchange_expiration_date(self):
        if self.expiration_date:
            self.removal_date = (self.expiration_date + timedelta(days= -90)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.use_date = (self.expiration_date + timedelta(days= -90)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.alert_date = (self.expiration_date + timedelta(days= -90)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _get_product_locked(self, product):
        """Should create locked? (including categories and parents)

        @param product: browse-record for product.product
        @return True when the category of the product or one of the parents
                demand new lots to be locked"""
        _locked = product.categ_id.lot_default_locked
        categ = product.categ_id.parent_id
        while categ and not _locked:
            _locked = categ.lot_default_locked
            categ = categ.parent_id
        return _locked

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.locked = self._get_product_locked(self.product_id)

    def button_lock(self):
        stock_quant_obj = self.env['stock.quant']
        for lot in self:
            for quant in stock_quant_obj.search([('lot_id', '=', lot.id)]):
                quant.sudo().locked = True
            lot.locked = True

    def button_unlock(self):
        for lot in self:
            lot.locked = False

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals.get('product_id'))
        vals['locked'] = self._get_product_locked(product)
        return super(StockProductionLot, self).create(vals)

    def write(self, values):
        if 'product_id' in values:
            product = self.env['product.product'].browse(
                values.get('product_id'))
            values['locked'] = self._get_product_locked(product)
        return super(StockProductionLot, self).write(values)

    @api.model
    def cron_block_expired_lots(self):
        expired_lots = self.search([('use_date','<=',fields.Datetime.now())])
        for lot in expired_lots:
            lot.button_lock()


class StockQuant(models.Model):
    _inherit = "stock.quant"

    expiry_state = fields.Selection(string="Expiry State",
                                    related="lot_id.expiry_state")
    locked = fields.Boolean(string='Blocked', related="lot_id.locked", default=False, store=True)

    #ACS: Checke and update/remove
    @api.model
    def quants_get(self, location, product, qty, domain=None,
                   restrict_lot_id=False, restrict_partner_id=False):
        if domain is None:
            domain = []
        domain += [('locked', '=', False)]
        return super(StockQuant, self).quants_get(
            location, product, qty, domain=domain,
            restrict_lot_id=restrict_lot_id,
            restrict_partner_id=restrict_partner_id)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: