# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json


class BIProductPack(models.Model):
    _inherit = 'bi.product.pack'

    # bundling_qty = fields.Float(compute='_compute_qty', store=True)
    # bundling_lst_price = fields.Float(compute='_compute_price', store=True)
    proportion = fields.Float(string='Proportion (%)')
    domain_product_template = fields.Char(compute='_compute_domain_product_template')
    product_template = fields.Many2one('product.template', string='Product', required=True)


    @api.depends('bi_product_template')
    def _compute_domain_product_template(self):
        if not self.bi_product_template:
            self.domain_product_template = json.dumps([('id', 'in', [])])
        else:
            # query = """
            #     SELECT id FROM product_template WHERE categ_id = %s AND categ_id IS NOT NULL
            # """

            # self._cr.execute(query, (self.bi_product_template.categ_id.id,))
            # ids = [r[0] for r in self._cr.fetchall()]
            product_template = self.env['product.template'].search([('type', '=', 'product')])
            self.domain_product_template = json.dumps([('id', 'in', product_template.ids)])

    @api.onchange('product_template')
    def _onchange_product_template(self):
        if self.product_template:
            self.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.product_template.id)], limit=1).id


    # @api.depends('qty_uom', 'product_id', 'product_id.standard_price')
    # def _compute_price(self):
    #     for record in self:
    #         record.bundling_lst_price = record.qty_uom * record.product_id.standard_price

    # @api.depends('qty_uom', 'product_id')
    # def _compute_qty(self):
    #     for record in self:
    #         record.bundling_qty = 0
    #         if record.qty_uom > 0:
    #             record.bundling_qty = round(record.product_id.qty_available / record.qty_uom)
