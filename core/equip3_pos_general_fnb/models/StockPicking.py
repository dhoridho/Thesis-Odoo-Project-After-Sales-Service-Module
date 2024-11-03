# -*- coding: utf-8 -*-

from ast import literal_eval
from odoo import fields, api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_all_values_stock_moves(self, lines, product, checking_uom):
        context = self._context
        all_values = super(StockPicking, self)._prepare_all_values_stock_moves(lines, product, checking_uom)

        order_lines = all_values['order_lines']
        first_line = all_values['first_line']
        order_id = first_line.order_id
        if order_id and not order_id.has_line_details():
            return all_values

        MrpBomLine = self.env['mrp.bom.line']
        PosComboOption = self.env['mrp.bom.line']

        move_values = []
        for line in order_lines:
            if line.bom_components:
                domain = [('id','in', [x['id'] for x in literal_eval(line.bom_components) if x.get('checked') == True] )]
                for com in MrpBomLine.search_read(domain, ['product_id','product_qty','is_extra','product_uom_id']):
                    quantity = com['product_qty'] * line.qty
                    product_id = com['product_id'][0]
                    move_values += [{
                        'product_id': product_id,
                        'product_uom_qty': quantity,
                        'name': first_line.name,
                        'product_uom': com['product_uom_id'][0],
                        'picking_id': self.id,
                        'picking_type_id': self.picking_type_id.id,
                        'state': 'draft',
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'company_id': self.company_id.id,
                    }]

            if line.pos_combo_options:
                for option in literal_eval(line.pos_combo_options):
                    if option.get('bom_components'): # If Options is BoM Product
                        domain = [('id','in', [x['id'] for x in option['bom_components'] if x.get('checked') == True] )]
                        for com in MrpBomLine.search_read(domain, ['product_id','product_qty','is_extra','product_uom_id']):
                            quantity = com['product_qty'] * line.qty
                            product_id = com['product_id'][0]
                            move_values += [{
                                'product_id': product_id,
                                'product_uom_qty': quantity,
                                'name': first_line.name,
                                'product_uom': com['product_uom_id'][0],
                                'picking_id': self.id,
                                'picking_type_id': self.picking_type_id.id,
                                'state': 'draft',
                                'location_id': self.location_id.id,
                                'location_dest_id': self.location_dest_id.id,
                                'company_id': self.company_id.id,
                            }]

                    else:
                        product_id = option['product_id'][0]
                        move_values += [{
                            'name': first_line.name,
                            'product_uom': line.product_id.uom_id.id,
                            'picking_id': self.id,
                            'picking_type_id': self.picking_type_id.id,
                            'product_id': product_id,
                            'product_uom_qty': line.qty,
                            'state': 'draft',
                            'location_id': self.location_id.id,
                            'location_dest_id': self.location_dest_id.id,
                            'company_id': self.company_id.id,
                        }]

            if not line.bom_components and not line.pos_combo_options:
                move_values += [{
                    'name': first_line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': self.id,
                    'picking_type_id': self.picking_type_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'state': 'draft',
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'company_id': self.company_id.id,
                }]

        if move_values:
            all_values['move_values'] = move_values
        return all_values