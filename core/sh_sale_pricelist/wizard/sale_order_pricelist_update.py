# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api
from datetime import date


class SaleOrderPricelistWizard(models.Model):
    _name = 'sale.order.pricelist.wizard'
    _description = 'Pricelist Wizard'

    shs_pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    pricelist_line = fields.One2many(
        'sale.order.pricelist.wizard.line', 'pricelist_id', string='PricelistLine Id')

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderPricelistWizard, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        if res_ids[0]:
            so_line = res_ids[0]
            so_line_obj = self.env['sale.order.line'].browse(so_line)
            pricelist_list = []
            pricelists = self.env['product.pricelist'].sudo().search([])
            if pricelists:
                for pricelist in pricelists:
                    price_unit = pricelist._compute_price_rule([(so_line_obj.product_id, so_line_obj.product_uom_qty, so_line_obj.order_id.partner_id)], date=date.today(
                    ), uom_id=so_line_obj.product_uom.id)[so_line_obj.product_id.id][0]
                    margin = price_unit - so_line_obj.product_id.standard_price
                    print(f'\n\n price_unit : {price_unit}\n\n')
                    if price_unit >= 1:
                        margin_per = (
                            100 * (price_unit - so_line_obj.product_id.standard_price))/price_unit
                    else:
                        margin_per = 0.0
                    wz_line_id = self.env['sale.order.pricelist.wizard.line'].create({'sh_pricelist_id': pricelist.id,
                                                                                      'sh_unit_price': price_unit,
                                                                                      'sh_unit_measure': so_line_obj.product_uom.id,
                                                                                      'sh_unit_cost': so_line_obj.product_id.standard_price,
                                                                                      'sh_margin': margin,
                                                                                      'sh_margin_per': margin_per,
                                                                                      'line_id': so_line, })

                    pricelist_list.append(wz_line_id.id)
            res.update({

                'pricelist_line': [(6, 0, pricelist_list)],
            })
        return res


class SaleOrderPricelistWizardLine(models.Model):
    _name = 'sale.order.pricelist.wizard.line'
    _description = 'Pricelist Wizard'

    pricelist_id = fields.Many2one(
        'sale.order.pricelist.wizard', "Pricelist Id")
    sh_pricelist_id = fields.Many2one(
        'product.pricelist', "Pricelist", required=True)
    sh_unit_measure = fields.Many2one('uom.uom', 'Unit')
    sh_unit_price = fields.Float('Unit Price')
    sh_unit_cost = fields.Float('Unit Cost')
    sh_margin = fields.Float('Margin')
    sh_margin_per = fields.Float('Margin %')
    line_id = fields.Many2one('sale.order.line')

    def update_sale_line_unit_price(self):
        if self.line_id:
            self.line_id.write({'price_unit': self.sh_unit_price})
