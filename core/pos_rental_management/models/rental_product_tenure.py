# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo.exceptions import ValidationError, Warning
from odoo import api, tools, _, models, fields
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from datetime import date, timedelta, datetime


class RentalProductTenure(models.Model):
    _name = 'rental.product.tenure'
    _description = 'Rental Tenure Details'

    name = fields.Char('Name')
    tenure_uom_id = fields.Many2one('uom.uom', string='Tenure UOM', domain=[
                                    ('is_rental_uom', '=', True)], required=True)
    product_tmpl_id = fields.Many2one('product.template')
    currency_id = fields.Many2one(related='product_tmpl_id.currency_id', string='Currency',
                                  readonly=True, store=True)
    tenure_start_count = fields.Integer('From(Tenure Count)', required=True)
    tenure_end_count = fields.Integer('To(Tenure Count)', required=True)
    tenure_amount = fields.Monetary(
        string='Tenure Amount(Per UOM)', currency_field='currency_id', required=True)

    @api.constrains('tenure_start_count', 'tenure_end_count', 'tenure_uom_id')
    def _validate_tenure_count(self):
        for rec in self:
            if rec.tenure_start_count <= 0 and rec.tenure_end_count <= 0:
                raise ValidationError(_('Tenure count must be greater than 0'))
            if rec.tenure_end_count < rec.tenure_start_count:
                raise ValidationError(
                    _('Tenure end count must be greater/equal than tenure start count.'))
            if rec.product_tmpl_id:
                existing_records = self.search(
                    [('id', '!=', rec.id), ('product_tmpl_id', '=', rec.product_tmpl_id.id), ('tenure_uom_id', '=', rec.tenure_uom_id.id)])
                range_list = []
                for data in existing_records:
                    if rec.tenure_start_count == data.tenure_start_count and rec.tenure_end_count == data.tenure_end_count:
                        raise ValidationError(_('Range (%s -> %s) %s is already exists.' % (
                            rec.tenure_start_count, rec.tenure_end_count, rec.tenure_uom_id.name)))
                    for num in range(data.tenure_start_count, data.tenure_end_count+1):
                        range_list.append(num)
                if range_list and rec.tenure_start_count in range_list or rec.tenure_end_count in range_list:
                    raise ValidationError(_("Tenure range [(%s -> %s) %s] can't overlap. Please change the tenure counts" % (
                        rec.tenure_start_count, rec.tenure_end_count, rec.tenure_uom_id.name)))

    @api.constrains('name')
    def _add_name_if_not_added(self):
        for rec in self:
            if not rec.name:
                rec.name = rec.tenure_uom_id.name + \
                    ' (' + str(rec.tenure_start_count) + \
                    '->' + str(rec.tenure_end_count) + ')'

    @api.constrains('tenure_amount')
    def _validate_tenure_amount(self):
        for rec in self:
            if rec.tenure_amount <= 0:
                raise ValidationError(
                    _('Tenure amount must be greater than Zero.'))
