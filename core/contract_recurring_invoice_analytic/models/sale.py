# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    recurring_rule_type = fields.Selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)'), ],
        string='Recurring Period',
        copy=False,
    )
    recurring_interval = fields.Integer(
        string="Repeat Every",
        copy=False,
    )

    #@api.multi
    def action_confirm(self):
        rec = super(SaleOrder, self).action_confirm()
        create_analytic_account = self._context.get('analytic_account', False)
        if create_analytic_account:
            return rec
        if all(not i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type or self.recurring_interval):
            return rec

        for line in self.order_line:
            if line.product_id.subscription_product:
                if line.product_id.recurring_interval and line.product_id.recurring_rule_type:
                    self.write({
                        'recurring_interval': line.product_id.recurring_interval,
                        'recurring_rule_type': line.product_id.recurring_rule_type
                    })

        if not self.recurring_interval and not self.recurring_rule_type:
            self.write({
                'recurring_interval': 1,
                'recurring_rule_type': 'monthly',
            })

#         if any(i.product_id.subscription_product for i in self.order_line) and not (self.recurring_rule_type and self.recurring_interval):
#             raise UserError(_('Please define a Recurring Period.'))
        #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id) #odoo11
        exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.currency_id.id != self.pricelist_id.currency_id.id)

#         if exist_line:
#             raise UserError(_('Currency of order is must be same as contract.'))
        #if not self.related_project_id:#odoo11
        if not self.analytic_account_id:
            #values = self._prepare_analytic_account_data()
            values = self._prepare_analytic_account_data(prefix=None)
            analytic_id = self.env['account.analytic.account'].create(values)
            # self.related_project_id = analytic_id.id #odoo11
            self.analytic_account_id = analytic_id.id
        analytic_account_ids = self.env['account.analytic.account'].search([])
        for line in self.order_line:
            if line.product_id.subscription_product:
              #  exist_line = self.related_project_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)#odoo11
                exist_line = self.analytic_account_id.subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
                if exist_line:
                    exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
                    exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
                else:
                    order_line={
                            #'subscription_product_line_id': self.related_project_id.id, #odoo11
			    'subscription_product_line_id': self.analytic_account_id.id,
                            'product_id':line.product_id.id,
#                            'layout_category_id':line.layout_category_id.id, odoo12
                            'name': line.name,
                            'product_uom_qty':line.product_uom_qty,
                            'product_uom':line.product_uom.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                            'price_unit':line.price_unit,
                            'tax_ids':[(6, 0, line.tax_id.ids)],
                            'discount': line.discount,
                            'price_subtotal': line.price_subtotal,
                            'price_total':line.price_total,
                            'currency_id':self.pricelist_id.currency_id.id,
                        }
                    subscription = self.env['analytic.sale.order.line'].sudo().create(order_line)
            elif line.product_id:
                exist_line = self.analytic_account_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id)
               # exist_line = self.related_project_id.not_subscription_product_line_ids.filtered(lambda t: t.product_id.id == line.product_id.id) #odoo11
                if exist_line:
                    exist_line.product_uom_qty = exist_line.product_uom_qty + line.product_uom_qty
                    exist_line.price_subtotal = exist_line.price_unit * exist_line.product_uom_qty
                else:
                    order_line={
                           # 'not_subscription_product_line_id': self.related_project_id.id, #odoo11
                            'not_subscription_product_line_id': self.analytic_account_id.id,
                            'product_id':line.product_id.id,
#                            'layout_category_id':line.layout_category_id.id, odoo12
                            'name': line.name,
                            'product_uom_qty':line.product_uom_qty,
                            'product_uom':line.product_uom.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                            'price_unit':line.price_unit,
                            'tax_ids':[(6, 0, line.tax_id.ids)],
                            'discount': line.discount,
                            'price_subtotal': line.price_subtotal,
                            'price_total':line.price_total,
                            'currency_id':self.pricelist_id.currency_id.id,
                        }
                    subscription = self.env['analytic.sale.order.line'].sudo().create(order_line)

        values = {
            'recurring_rule_type': self.recurring_rule_type,
            'recurring_interval': self.recurring_interval
        }
        today = datetime.date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        invoicing_period = relativedelta(**{periods[values['recurring_rule_type']]: values['recurring_interval']})
        recurring_next_date = today + invoicing_period
        prevday = recurring_next_date - datetime.timedelta(days=1)
        if not self.analytic_account_id.recurring_next_date: # project_id
            self.analytic_account_id.update({
                            'end_date': prevday,
                            'recurring_next_date': recurring_next_date,
                            'recurring_rule_type': values['recurring_rule_type'],
                            'recurring_interval': values['recurring_interval'],
                        }) # project_id
        if self.note:
            self.analytic_account_id.update({'terms_and_conditions': self.note})# project_id
        if not self.analytic_account_id.start_date:# project_id
            self.analytic_account_id.update({'start_date': fields.Date.today()})# project_id
        return rec

    def _prepare_analytic_account_data(self, prefix=None):
        res = super(SaleOrder, self)._prepare_analytic_account_data(prefix=prefix)
        res.update({
            'name': self.name +' - '+ self.partner_id.name,
            'currency_id': self.company_id.currency_id.id,
            'order_invoice_currency_id': self.currency_id.id,
            'recurring_interval': self.recurring_interval,
            'recurring_rule_type': self.recurring_rule_type
        })
        return res

    def _prepare_analytic_account_data_old_notused(self):
        values = {
            'name':self.name +' - '+ self.partner_id.name,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.company_id.currency_id.id,
            'order_invoice_currency_id': self.currency_id.id,
            'recurring_interval': self.recurring_interval,
            'recurring_rule_type': self.recurring_rule_type
        }
        return values

class AnalyticSaleOrderLine(models.Model):
    _name = "analytic.sale.order.line"
    _description = 'Analytic Sale Order Lines'
    
    @api.depends('product_id')
    def _compute_product_name(self):
        for rec in self:
            if rec.product_id.description:
                rec.name = rec.product_id.description
            else:
                rec.name = rec.product_id.name
     
    name = fields.Text(string='Description', compute='_compute_product_name', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_qty = fields.Float(string='Quantity', default=1.0, required=True)
#    product_uom = fields.Many2one('product.uom', related='product_id.uom_id', string='Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', related='product_id.uom_id', string='Unit of Measure', required=True)
    #price_unit = fields.Float('Unit Price', related='product_id.lst_price', default=0.0)
    price_unit = fields.Float('Unit Price', default=0.0)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    discount = fields.Float(string='Discount (%)', default=0.0)
#    layout_category_id = fields.Many2one('sale.layout_category', string='Section') odoo12
#     price_total = fields.Float(string='Total', readonly=True)
#     price_subtotal = fields.Float(string='Subtotal', readonly=True, compute = '_price_subtotal',)
    subscription_product_line_id = fields.Many2one(
        'account.analytic.account',
        string="Contract Product Lines",
    )
    not_subscription_product_line_id = fields.Many2one(
        'account.analytic.account',
        string="Non-Contract Product Lines",
    )
    price_subtotal = fields.Float(
        compute='_compute_amount',
        string='Subtotal',
        readonly=True,
        store=True
    )
    price_tax = fields.Float(
        compute='_compute_amount',
        string='Taxes',
        readonly=True,
        store=True
    )
    price_total = fields.Float(
        compute='_compute_amount',
        string='Total',
        readonly=True,
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
    )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(price, line.subscription_product_line_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.subscription_product_line_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
