# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # bundling_qty = fields.Float('Bundling Qty', compute='_compute_bundling_price', store=True)
    # bundling_price = fields.Float(string='Bundling Cost', compute='_compute_bundling_price', store=True)

    # @api.depends('bi_pack_ids', 'bi_pack_ids.qty_uom', 'bi_pack_ids.bundling_qty', 'bi_pack_ids.bundling_lst_price')
    # def _compute_bundling_price(self):
    #     for record in self:
    #         min_qty = record.bi_pack_ids.mapped('bundling_qty')
    #         record.bundling_qty = min(min_qty) if min_qty else 0
    #         record.bundling_price = sum(record.bi_pack_ids.mapped('bundling_lst_price'))

    # @api.onchange('bi_pack_ids')
    # def _onchange_bi_pack_ids(self):
    #     if len(self.bi_pack_ids) > 3:
    #         raise ValidationError(_("Maximum Product Bundle is 3, cannot add more than 3"))


    @api.constrains('bi_pack_ids', 'is_pack')
    def _check_bi_pack_ids(self):
        for record in self:
            if record.is_pack:
                if not record.bi_pack_ids:
                    raise ValidationError(_("Please add at least one product to create product bundles"))
                
                if sum(record.bi_pack_ids.mapped('proportion')) != 100:
                    raise ValidationError(_("Total proportion for products bundles must be 100%"))
