# -*- coding: utf-8 -*-

from odoo import models
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        res = super(SaleOrder,self)._action_confirm()
        loyalty_history_obj = self.env['all.loyalty.history']   
        today_date = datetime.today().date()
        config = self.env['all.loyalty.setting'].sudo().search([
            ('active','=',True),('issue_date', '<=', today_date),
            ('expiry_date', '>=', today_date), ('company_id', '=', self.env.company.id)])
        if config:
            for rec in self:
                partner_id =rec.partner_id
                plus_points = 0.0

                company_currency = rec.company_id.currency_id
                web_currency = rec.pricelist_id.currency_id     
                
                if config.loyalty_basis_on == 'amount' :
                    if config.loyality_amount > 0 :
                        price = sum(rec.order_line.filtered(lambda x: not x.is_delivery).mapped('price_total')) 
                        if company_currency.id != web_currency.id:
                            new_rate = (price*company_currency.rate)/web_currency.rate
                        else:
                            new_rate = price
                        plus_points =  int( new_rate / config.loyality_amount)

                if config.loyalty_basis_on == 'loyalty_category' :
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
                            'company_id': rec.company_id.id,
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
                            'company_id': rec.company_id.id,
                        }
                        loyalty_history = loyalty_history_obj.sudo().create(vals)
                    rec.write({'order_credit_points':plus_points})
        return res
