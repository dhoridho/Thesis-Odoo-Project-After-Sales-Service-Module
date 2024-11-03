# -*- coding: utf-8 -*-

from tracemalloc import DomainFilter
from odoo import models, fields, api
from odoo.osv.expression import DOMAIN_OPERATORS
from odoo.tools import float_is_zero, float_repr

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    child_product = fields.Many2one('product.product', string="Child Product")
    is_consignment = fields.Boolean(string='Is Consignment Product')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sale_state_new = fields.Selection(
        selection=[
            ('sold','Sold'),
            ('partial','Partial Sold'),
            ('not_sold','Not Sold'),
        ],
        default="not_sold",
        string='New Consignment Status',
        compute="_consignment_sale_state_new",
        readonly=False,
    )

    product_lots_ids = fields.One2many('stock.production.lot', 'product_id', string="Lot / Serial", tracking=True, domain=[('is_consignment', '=', True)])
    owner_id = fields.One2many('stock.picking', 'product_id', string="Owner",domain=[('owner_id', '!=', False), ('state', '=' , 'done')])
    purchase_order_line_ids = fields.One2many(
        'purchase.order.line',
        'product_id',
        string="Purchase Line",
        readonly=True,
        copy=False,
        domain=[('order_id.picking_ids.state', '=', 'done'), ('order_id.is_consignment', '=', True)],
        )

    product_display_name = fields.Char(string='Product Display Name', compute='_compute_product_display_name', store=True)
    child_product = fields.Many2one('product.product', string="Child Product")
    is_consignment = fields.Boolean(string='Is Consignment Product', related='product_tmpl_id.is_consignment')


    # @api.onchange('is_consignment')
    # def _onchange_is_consignment(self):
    #     for rec in self:
    #         print(' recc iddd',rec.id)
            # asd = self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
            # print('asdasdasdadsasda',asd)
            # if rec.is_consignment == False:
            #     product_product = self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
            #     print('product_product False',product_product)
            # if rec.is_consignment == True:
            #     product_product = self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
            #     print('product_product True',product_product)

    @api.depends('name', 'default_code')
    def _compute_product_display_name(self):
        for record in self:
            if isinstance(record.id, models.NewId):
                record.product_display_name = ''
            else:
                record.product_display_name = record.display_name or ''

    @api.depends()
    def _consignment_sale_state_new(self):
        for rec in self:
            if rec.sale_qty == 0.0:
                rec.sale_state_new = 'not_sold'
            elif rec.sale_qty <= rec.purchase_qty and rec.sale_qty >= 0:
                rec.sale_state_new = 'partial'
            elif rec.sale_qty >= rec.purchase_qty:
                rec.sale_state_new = 'sold'

    def _prepare_out_svl_vals(self, quantity, company):
        res = super(ProductProduct, self)._prepare_out_svl_vals(quantity, company)
        svl_source_ids = [vals.get('svl_source_id', False) for a, b, vals in res.get('line_ids', [])]
        svl_sources = self.env['stock.valuation.layer'].browse(svl_source_ids)
        svl_sources_consignment = svl_sources.filtered(lambda o: o.is_consignment)
        res.update({
            'is_consignment': len(svl_sources_consignment) > 0,
            'consignment_id': svl_sources_consignment and svl_sources_consignment[0].consignment_id.id or False
        })
        return res


# class StockPicking(models.Model):
#     _inherit = 'stock.picking'

#     def name_get(self):
#         res = super(StockPicking, self).name_get()
#         if self._context.get('default_is_assign_owner') and self._context.get('default_is_assign_owner') != None:
#             result = []
#             for x in self:
#                 name = x.owner_id.name
#                 result.append((x.id, name))
#             return result
#         else:
#             return res


# class PurchaseOrderLine(models.Model):
#     _inherit = 'purchase.order.line'

#     def name_get(self):
#         res = super(PurchaseOrderLine, self).name_get()
#         context = dict(self.env.context or {})
#         if self._context.get('default_is_consignment') and self._context.get('default_is_consignment') != None:
#             result = []
#             for x in self:
#                 name = x.order_id.name
#                 result.append((x.id, name))
#             return result
#         else:
#             return res
