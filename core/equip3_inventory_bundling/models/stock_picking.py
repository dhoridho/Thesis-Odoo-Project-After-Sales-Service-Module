from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def bundle_price_unit(self, move, line):
        product_bundle_id = False
        cost = 0

        if move.picking_code == 'incoming':
            product_bundle_id = move.purchase_line_id.product_id.bi_pack_ids.filtered(lambda x: x.product_id == line.product_id)
            cost = move.purchase_line_id.price_unit
        elif move.picking_code == 'outgoing':
            product_bundle_id = move.sale_line_id.product_id.bi_pack_ids.filtered(lambda x: x.product_id == line.product_id)
            cost = move.sale_line_id.price_unit

        if product_bundle_id:
            proportion = product_bundle_id.proportion / 100
            return (cost / line.qty_uom) * proportion

        return 0.0

    def prepare_bundle_values(self, move, line, qty, seq, bundle_id_before_change, price_unit):
        """
        Prepare a dictionary of values for a bundle line.
        """
        return {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'move_line_sequence': seq,
            'company_id': move.company_id.id,
            'product_uom': line.product_id.uom_id.id,
            'product_uom_qty': line.qty_uom * qty,
            'initial_demand': line.qty_uom * qty,
            'partner_id': move.partner_id.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'rule_id': move.rule_id.id,
            'origin': move.origin,
            'picking_type_id': move.picking_type_id.id,
            'warehouse_id': move.warehouse_id.id,
            'qty_pack': line.qty_uom,
            'picking_id': move.picking_id.id,
            'sale_line_id': move.sale_line_id.id,
            'purchase_line_id': move.purchase_line_id.id,
            'is_pack': True,
            'qty_bundle': qty,
            'id_bundle': bundle_id_before_change,
            'analytic_account_group_ids': [(6, 0, move.analytic_account_group_ids.ids)],
            'price_unit': price_unit
        }

    def change_product_line_pack(self, lines, line_seq):
       
        for res in self:
            seq = line_seq

            for move in lines:
                move.move_line_sequence = seq

                if move.product_id.is_pack:
                    qty = move.product_uom_qty
                    bundle_id_before_change = res.product_id.product_tmpl_id

                    if move.product_id.bi_pack_ids:
                        val = []

                        for idx, line in enumerate(move.product_id.bi_pack_ids, start=1):
                            price_unit = self.bundle_price_unit(move, line)

                            if idx == 1:
                                move.write({
                                    'name': line.product_id.name,
                                    'product_id': line.product_id.id,
                                    'product_uom': line.product_id.uom_id.id,
                                    'product_uom_qty': line.qty_uom * qty,
                                    'initial_demand': line.qty_uom * qty,
                                    'qty_pack': line.qty_uom,
                                    'remaining': line.qty_uom * qty,
                                    'is_pack': True,
                                    'qty_bundle': qty,
                                    'id_bundle': bundle_id_before_change,
                                    'analytic_account_group_ids': [(6, 0, move.analytic_account_group_ids.ids)],
                                    'price_unit': price_unit
                                })
                            else:
                                seq += 1
                                val.append(self.prepare_bundle_values(move, line, qty, seq, bundle_id_before_change, price_unit))

                        if val:
                            self.env['stock.move'].create_line_pack(val)
