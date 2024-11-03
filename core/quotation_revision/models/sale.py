# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _order_revised_count(self):
        for sale_rec in self:
            order_revised_count = self.search(
                [('parent_saleorder_id', '=', sale_rec.id)])
            sale_rec.order_revised_count = len(order_revised_count)

    name = fields.Char(string='Order Reference', required=True, copy=False,
                       readonly=True, index=True, default='New')
    parent_saleorder_id = fields.Many2one(
        'sale.order', 'Parent SaleOrder', copy=False)
    order_revised_count = fields.Integer(
        '# of Orders Revised', compute='_order_revised_count', copy=False)
    so_number = fields.Integer('SO Number', copy=False, default=1)
    state = fields.Selection(selection_add=[
        ('draft_quote', 'Revised Quotation'),
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('revised', 'Revised Order'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True,
        tracking=True, default='draft')

    def so_revision_quote(self):
        for cur_rec in self:
            if not cur_rec.origin:
                origin_name = cur_rec.name
                cur_rec.origin = cur_rec.name
            else:
                origin_name = cur_rec.origin

            vals = {
                'name': 'RSO' + str(cur_rec.so_number) + "_" + origin_name,
                'state': 'revised',
                'parent_saleorder_id': cur_rec.id
            }
            cur_rec.copy(default=vals)
            cur_rec.state = 'draft'
#             so_copy.is_revision_quote = True
            cur_rec.so_number += 1

    def _action_confirm(self):
        sup_rec = super(SaleOrder, self)._action_confirm()
        child_id = self.search(
            [('parent_saleorder_id', '=', self.id)], order="create_date desc",
            limit=1)
        if child_id:
            child_id.name = self.name
        return sup_rec
