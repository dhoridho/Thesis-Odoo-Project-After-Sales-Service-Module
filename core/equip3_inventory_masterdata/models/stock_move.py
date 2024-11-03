from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from odoo.tools import OrderedSet
from odoo.tools.float_utils import float_compare, float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    uom_cache = dict()


    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        ctx = dict(self.env.context)
        if not self.env.context.get("not_create_interwarehouse_transfer"):
            ctx.update({'stock_move_id': self.id})
        else:
            if ctx.get("stock_move_id"):
                ctx.pop("stock_move_id")
        ctx.pop("not_create_interwarehouse_transfer", None)
        self = self.with_context(ctx)

        res = super(StockMove, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        return res

    length = fields.Float(string="Length", compute='_cal_move_length', store=False)
    width = fields.Float(string="Width", compute='_cal_move_width', store=False)
    height = fields.Float(string="Height", compute='_cal_move_height', store=False)

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_length(self):
        moves_with_length = self.filtered(lambda moves: moves.product_id.length > 0.00)
        for move in moves_with_length:
            move.length = (move.product_qty * move.product_id.length)
        (self - moves_with_length).length = 0

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_width(self):
        moves_with_width = self.filtered(lambda moves: moves.product_id.width > 0.00)
        for move in moves_with_width:
            move.width = (move.product_qty * move.product_id.width)
        (self - moves_with_width).width = 0

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_height(self):
        moves_with_height = self.filtered(lambda moves: moves.product_id.height > 0.00)
        for move in moves_with_height:
            move.height = (move.product_qty * move.product_id.height)
        (self - moves_with_height).height = 0


    @api.onchange('product_uom_qty')
    def _set_cache_product_uom_qty(self):
        if self.product_uom.id == self.product_id.uom_id.id:
            self.uom_cache['product_uom_qty'] = self.product_uom_qty


    @api.onchange('product_uom')
    def _set_cache_product_uom(self):
        pass

        # TODO: adjust to the current custom UoM relation
        # self.ensure_one()

        # product_uom_id = self.product_uom.id
        # product_uom_qty = self.uom_cache.get('product_uom_qty')

        # def get_uom_by_type(uom_type):
        #     uom_domain = [
        #         ('category_id', '=', self.product_id.uom_id.category_id.id),
        #         ('id', '=', product_uom_id),
        #         ('uom_type', '=', uom_type)
        #     ]
        #     return self.env['uom.uom'].search(uom_domain)

        # custom_uom = self.product_id.custom_uom_line.filtered(lambda line: line.uom_id.id == product_uom_id)
        # default_bigger_uom = get_uom_by_type('bigger')
        # default_smaller_uom = get_uom_by_type('smaller')
        # default_ref_uom = get_uom_by_type('reference')

        # if custom_uom:
        #     self.product_uom_qty = product_uom_qty * custom_uom.ratio
        #     self.uom_cache['current_qty'] = self.product_uom_qty
        #     self.uom_cache['current_ratio'] = custom_uom.ratio
        # elif default_bigger_uom:
        #     self.product_uom_qty = product_uom_qty * default_bigger_uom.factor_inv
        #     self.uom_cache['current_qty'] = self.product_uom_qty
        #     self.uom_cache['current_ratio'] = default_bigger_uom.factor_inv
        # elif default_smaller_uom:
        #     self.product_uom_qty = product_uom_qty * default_smaller_uom.factor
        #     self.uom_cache['current_qty'] = self.product_uom_qty
        #     self.uom_cache['current_ratio'] = default_smaller_uom.factor
        # elif default_ref_uom:
        #     self.product_uom_qty = self.uom_cache['current_qty'] * self.uom_cache['current_ratio']
        # else:
        #     self.product_uom_qty = product_uom_qty
