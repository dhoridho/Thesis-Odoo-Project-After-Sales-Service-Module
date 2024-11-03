# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
import pytz
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import tools
from odoo.tools.float_utils import float_compare, float_round
from operator import itemgetter

class CashbackLines(models.Model):
    _name = 'cashback.line'
    _description = "Cashback Line"

    sequence = fields.Integer("No")
    product_id = fields.Many2one('product.product', 'Cashback')
    name = fields.Char("Description")
    product_uom_qty = fields.Float("Qty")
    price_unit = fields.Float("Unit Price")
    total = fields.Float("Total")
    customer_voucher_id = fields.Many2one(comodel_name='customer.voucher', string='Customer Voucher')
    order_id = fields.Many2one('sale.order', string='Order')
    invoice_id = fields.Many2one('account.move', string='Invoice')

    def unlink(self):
        self.order_id.show_cashback = False
        # self.customer_voucher_id.state = 'available'
        res = super().unlink()
        return res

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def create_invoices(self):
        is_dp = False
        if self.advance_payment_method == 'percentage' or self.advance_payment_method == 'fixed':
            is_dp = True
        self.env.context = dict(self._context)
        self.env.context.update({'is_dp': is_dp})
        res = super().create_invoices()
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    have_available_customer_voucher = fields.Boolean(string='Have available customer voucher', compute="_compute_have_available_customer_voucher")
    customer_voucher_used_ids = fields.Many2many(comodel_name='customer.voucher', string='Customer Voucher Used', readonly=True)
    cashback_line_ids = fields.One2many('cashback.line','order_id', string='Cashback')
    show_cashback = fields.Boolean("Show Cashback")
    cn_cashback_ids = fields.One2many(comodel_name='account.move', inverse_name='so_cashback_id', string='CN Cashback')
    cn_cashback_count = fields.Integer(string='CN Cashback Count', compute="_compute_cn_cashback_count")
    already_used_for_vouchers = fields.Boolean("Already Used", default=False)

    @api.depends('cn_cashback_ids')
    def _compute_cn_cashback_count(self):
        for i in self:
            i.cn_cashback_count = i.cn_cashback_ids and len(i.cn_cashback_ids) or 0

    @api.depends('partner_id')
    def _compute_have_available_customer_voucher(self):
        for i in self:
            have_available_customer_voucher = False
            if i.partner_id:
                if i.partner_id.have_voucher:
                    today = fields.Date.today()
                    self.env.cr.execute("""
                        SELECT id
                        FROM customer_voucher
                        WHERE customer_id = %s AND state = 'available' and expired_date = %s""", (i.partner_id.id, today.strftime("%Y%m%d")))
                    voucher_expired = self.env.cr.dictfetchall()
                    voucher_expired = list(map(itemgetter('id'), voucher_expired))
                    if voucher_expired:
                        self._cr.execute("""UPDATE customer_voucher SET state='expired' WHERE id in %s""", [tuple(voucher_expired)])
                        self._cr.commit()
                    self.env.cr.execute("""
                        SELECT id
                        FROM customer_voucher
                        WHERE state = 'available' AND customer_id = %s limit 1""" % i.partner_id.id)
                    vouchers = self.env.cr.dictfetchall()
                    if vouchers:
                        have_available_customer_voucher = True
            i.have_available_customer_voucher = have_available_customer_voucher
    

    def _action_confirm(self):
        res = super(SaleOrder,self)._action_confirm()
        loyalty_history_obj = self.env['all.loyalty.history']   
        today_date = datetime.today().date()
        self.env.cr.execute("""
                SELECT loyalty_basis_on,loyality_amount
                FROM all_loyalty_setting
                WHERE active = True and issue_date <= '%s' and expiry_date >= '%s' ORDER BY id DESC LIMIT 1
            """ % (str(today_date), str(today_date)))
        config = self.env.cr.fetchall()
        # config = self.env['all.loyalty.setting'].sudo().search([('active','=',True),('issue_date', '<=', today_date ),
        #                         ('expiry_date', '>=', today_date )])
        if config : 
            for rec in self:
                partner_id =rec.partner_id
                plus_points = 0.0

                company_currency = rec.company_id.currency_id
                web_currency = rec.pricelist_id.currency_id     
                
                if config[0][0] == 'amount' :
                    if config[0][1] > 0 :
                        price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total')) 
                        if company_currency.id != web_currency.id:
                            new_rate = (price*company_currency.rate)/web_currency.rate
                        else:
                            new_rate = price
                        plus_points =  int( new_rate / config[0][1])

                if config[0][0] == 'loyalty_category' :
                    for line in  rec.order_line:
                        if not line.discount_line or not line.is_delivery :
                            if rec.is_from_website :
                                prod_categs = line.product_id.public_categ_ids
                                for c in prod_categs :
                                    if c.Minimum_amount > 0 :
                                        if company_currency.id != web_currency.id:
                                            price = line.price_total
                                            new_rate = (price*company_currency.rate)/web_currency.rate
                                        else:
                                            new_rate = line.price_total
                                        plus_points += int(new_rate / c.Minimum_amount)
                            else:
                                prod_categ = line.product_id.categ_id
                                if prod_categ.Minimum_amount > 0 :
                                    if company_currency.id != web_currency.id:
                                        price = line.price_total
                                        new_rate = (price*company_currency.rate)/web_currency.rate
                                    else:
                                        new_rate = line.price_total
                                    plus_points += int(new_rate / prod_categ.Minimum_amount)
                
                if rec.order_redeem_points > 0:
                    is_debit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','debit')])
                    if is_debit:
                        is_debit.write({
                            'points': rec.order_redeem_points,
                            'state': 'done',
                            'date' : datetime.now(),
                            'partner_id': partner_id.id,
                        })
                    else:
                        vals = {
                            'order_id':rec.id,
                            'partner_id': partner_id.id,
                            'date' : datetime.now(),
                            'transaction_type' : 'debit',
                            'generated_from' : 'sale',
                            'points': rec.order_redeem_points,
                            'state': 'done',
                        }
                        loyalty_history = loyalty_history_obj.sudo().create(vals)
                
                if plus_points > 0 :
                    is_credit = loyalty_history_obj.search([('order_id','=',rec.id),('transaction_type','=','credit')])
                    if is_credit:
                        is_credit.write({
                            'points': plus_points,
                            'state': 'done',
                            'date' : datetime.now(),
                            'partner_id': partner_id.id,
                        })
                    else:
                        vals = {
                            'order_id':rec.id,
                            'partner_id': partner_id.id,
                            'date' : datetime.now(),
                            'transaction_type' : 'credit',
                            'generated_from' : 'sale',
                            'points': plus_points,
                            'state': 'done',
                        }
                        loyalty_history = loyalty_history_obj.sudo().create(vals)
                    rec.write({'order_credit_points':plus_points})
        
        self.partner_id.update_customer_target()
        return res
    
    def apply_customer_voucher(self):
        # user_vouchers = self.env['customer.voucher'].search([
        #                     ('customer_id', '=', self.partner_id.id)
        #                 ])
        # today = fields.Date.today()
        # for voucher in user_vouchers:
        #     print("====Test success pass here")
        #     if voucher.expired_date and voucher.expired_date < today:
        #         voucher.write({'state': 'expired'})
        view_id = self.env.ref('equip3_sale_loyalty.apply_voucher_view_wizard_form').id
        apply_voucher = self.env['apply.voucher'].create({
            'customer_id': self.partner_id.id,
            'voucher_ids': [(6, 0, self.partner_id.customer_voucher_ids.filtered(lambda v: v.state == 'available').ids)]
        })
        # context = {
        #     'default_customer_id': self.partner_id.id,
        #     'default_voucher_ids' : [voucher.id for voucher in self.partner_id.customer_voucher_ids.filtered(lambda v: v.state == 'available')]
        # }
        return {
            'name': 'Apply Voucher',
            'type': 'ir.actions.act_window',
            'res_model': 'apply.voucher',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id,
            'target': 'new',
            'res_id': apply_voucher.id
        }

    # def apply_customer_voucher(self):
    #     avail_vouchers = self.partner_id.customer_voucher_ids.filtered(lambda v:v.state == 'available')
    #     line_ids = []
    #     cashback_line_ids = []
    #     for voucher in avail_vouchers:
    #         customer_target = voucher.customer_target_id
    #         reward_type = customer_target.reward_type
    #         reward_product = voucher.discount_line_product_id
    #         disc_type = customer_target.disc_type
    #         if reward_type == 'discount':
    #             if disc_type == 'fix':
    #                 disc_amount = customer_target.disc_amount
    #                 vals_line = {
    #                     'sale_line_sequence': str(len(self.order_line) + 1),
    #                     'product_id': reward_product.id,
    #                     'price_unit': -customer_target.disc_amount,
    #                     'product_uom_qty': 1,
    #                     'name': reward_product.name,
    #                     'product_uom': reward_product.uom_id.id,
    #                     'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
    #                     'delivery_address_id': self.partner_id.id,
    #                     'customer_voucher_id': voucher.id,
    #                 }
    #                 line_ids.append((0,0,vals_line))
    #             else:
    #                 untaxed_amount = self.amount_untaxed
    #                 disc_amount = untaxed_amount*customer_target.disc_percentage/100
    #                 vals_line = {
    #                     'sale_line_sequence': str(len(self.order_line) + 1),
    #                     'product_id': reward_product.id,
    #                     'price_unit': -disc_amount,
    #                     'product_uom_qty': 1,
    #                     'name': reward_product.name,
    #                     'product_uom': reward_product.uom_id.id,
    #                     'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
    #                     'delivery_address_id': self.partner_id.id,
    #                     'customer_voucher_id': voucher.id,
    #                 }
    #                 line_ids.append((0,0,vals_line))
    #             voucher.state = 'used'
    #         elif reward_type == 'product':
    #             line_yang_product_nya_sama = self.order_line.filtered(lambda l,customer_target=customer_target:l.product_id.id == customer_target.product_id.id)
    #             disc_amount = customer_target.product_id.product_tmpl_id.list_price
    #             free_qty = customer_target.quantity or 1
    #             if not line_yang_product_nya_sama:
    #                 vals_line = {
    #                     'sale_line_sequence': str(len(self.order_line) + 1),
    #                     'product_id': customer_target.product_id.id,
    #                     'price_unit': disc_amount,
    #                     'product_uom_qty': free_qty,
    #                     'name': customer_target.product_id.name,
    #                     'product_uom': reward_product.uom_id.id,
    #                     'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
    #                     'delivery_address_id': self.partner_id.id,
    #                     'customer_voucher_id': voucher.id,
    #                     'tax_id':[(5,0,0)],
    #                 }
    #                 line_ids.append((0,0,vals_line))
    #             vals_line = {
    #                 'sale_line_sequence': str(len(self.order_line) + 1),
    #                 'product_id': reward_product.id,
    #                 'price_unit': -disc_amount,
    #                 'product_uom_qty': free_qty,
    #                 'name': reward_product.name,
    #                 'product_uom': reward_product.uom_id.id,
    #                 'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
    #                 'delivery_address_id': self.partner_id.id,
    #                 'customer_voucher_id': voucher.id,
    #                 'tax_id':[(5,0,0)],
    #             }
    #             line_ids.append((0,0,vals_line))
    #             voucher.state = 'used'
    #         elif reward_type == 'cashback':
    #             line_yang_product_nya_sama = False
    #             if customer_target.apply_cashback == 'percentage':
    #                 disc_amount = customer_target.discount_line_product_id.lst_price / 100 * self.amount_total
    #             else:
    #                 disc_amount = customer_target.discount_line_product_id.lst_price
    #             free_qty = customer_target.quantity or 1
    #             total = disc_amount * free_qty
    #             if cashback_line_ids:
    #                 if cashback_line_ids[-1][2]['product_id'] == customer_target.discount_line_product_id.id and cashback_line_ids[-1][2]['price_unit'] == customer_target.discount_line_product_id.lst_price:
    #                     line_yang_product_nya_sama = True
    #             if not line_yang_product_nya_sama:
    #                 vals_line = {
    #                     'sequence': str(len(cashback_line_ids) + 1),
    #                     'product_id': customer_target.discount_line_product_id.id,
    #                     'name': customer_target.discount_line_product_id.name,
    #                     'product_uom_qty': free_qty,
    #                     'price_unit': disc_amount,
    #                     'total': total,
    #                     'customer_voucher_id': voucher.id,
    #                 }
    #                 cashback_line_ids.append((0,0,vals_line))
    #             else:
    #                 cashback_line_ids[-1][2]['product_uom_qty'] += free_qty
    #                 cashback_line_ids[-1][2]['total'] += disc_amount * free_qty
    #             voucher.state = 'used'
    #     if line_ids:
    #         self.order_line = line_ids
    #     if cashback_line_ids:
    #         self.cashback_line_ids = [(6,0,[])]
    #         self.cashback_line_ids = cashback_line_ids
    #         self.show_cashback = True
    #     if avail_vouchers:
    #         self.customer_voucher_used_ids = [(6,0,avail_vouchers.ids)]
    
    def action_cancel(self):
        line_by_customer_voucher = self.order_line.filtered(lambda l:l.customer_voucher_id)
        if line_by_customer_voucher:
            line_by_customer_voucher.unlink()
        return super(SaleOrder,self).action_cancel()

    def action_view_cn_cashback(self):
        invoices = self.cn_cashback_ids
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.mapped('name'),
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    customer_voucher_id = fields.Many2one(comodel_name='customer.voucher', string='Customer Voucher', readonly=True)
    