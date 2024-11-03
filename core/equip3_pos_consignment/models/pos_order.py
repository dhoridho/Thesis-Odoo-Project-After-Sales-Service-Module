# -*- coding: utf-8 -*-

from odoo import fields, models, _

class PosOrder(models.Model):
    _inherit = 'pos.order'

    bill_consignment_ids = fields.Many2many('account.move', 'pos_order_account_move_as_bill_consignment_rel', 'pos_order_id', 'account_move_id', string='Bill Consignment', copy=False)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    consignment_agreement_id = fields.Many2one('consignment.agreement', 
        compute='_compute_consignment_agreement_id', 
        string='Consignment Agreement', store=False)
    is_billed_consignment = fields.Boolean('Is Billed Consignment', default=False, copy=False)


    def _compute_consignment_agreement_id(self):
        consignment_by_pol_id = {}
        consignment_by_lot_name = {}
        lot_by_pos_line_id = {}
        lot_names = []

        pos_order_line_ids = self.filtered(lambda r: r.product_id and r.product_id.product_tmpl_id and r.product_id.product_tmpl_id.is_consignment).ids
        if pos_order_line_ids:
            query = '''
                SELECT
                   pol.id, ppol.lot_name
                FROM pos_order_line AS pol
                INNER JOIN pos_pack_operation_lot AS ppol ON ppol.pos_order_line_id = pol.id
                WHERE pol.id IN ({pos_order_line_ids})
            '''.format(pos_order_line_ids=str(pos_order_line_ids)[1:-1])
            self.env.cr.execute(query)
            results = self.env.cr.fetchall()
            lot_by_pos_line_id = {r[0]:r[1] for r in results}
            lot_names = list(set([r[1] for r in results if r[1]]))
            
        if lot_names:
            query = '''
                SELECT
                    spl.name, sp.consignment_id
                FROM stock_move_line AS sml
                INNER JOIN stock_move AS sm ON sm.id = sml.move_id
                INNER JOIN stock_picking AS sp ON sp.id = sm.picking_id
                INNER JOIN stock_production_lot AS spl ON spl.id = sml.lot_id
                WHERE  sml.lot_id IS NOT NULL
                    AND sp.consignment_id IS NOT NULL
                    AND spl.name IN ({lot_names})
                GROUP BY spl.name, sp.consignment_id
                '''.format(lot_names=str(lot_names)[1:-1])
            self.env.cr.execute(query)
            consignment_by_lot_name = {x[0]:x[1] for x in self.env.cr.fetchall()}
        
        if pos_order_line_ids:
            #TODO: Get from stock.valuation.layer
            query = '''
                SELECT  
                    pol.id,
                    svl.consignment_id
                FROM stock_valuation_layer AS svl
                INNER JOIN stock_move as sm ON sm.id = svl.stock_move_id
                INNER JOIN stock_picking as sp ON sp.id = sm.picking_id
                INNER JOIN pos_order as po ON po.id = sp.pos_order_id
                INNER JOIN pos_order_line as pol ON pol.order_id = po.id  AND pol.product_id = sm.product_id
                INNER JOIN stock_valuation_layer_line AS svll ON svll.svl_id = svl.id
                INNER JOIN consignment_agreement as ca ON ca.id = svl.consignment_id
                WHERE 
                    svl.consignment_id IS NOT NULL
                    AND po.id IS NOT NULL 
                    AND pol.id IN ({pos_order_line_ids})
                GROUP BY pol.id, svl.consignment_id
            '''.format(pos_order_line_ids=str(pos_order_line_ids)[1:-1])
            self._cr.execute(query)
            consignment_by_pol_id = {x[0]:x[1] for x in self.env.cr.fetchall()}

        for rec in self:
            consignment_agreement_id = False
            lot_name = lot_by_pos_line_id.get(rec.id)
            if lot_name:
                consignment_agreement_id = consignment_by_lot_name.get(lot_name, False) or False
            if not consignment_agreement_id:
                consignment_agreement_id = consignment_by_pol_id.get(rec.id)
            rec.consignment_agreement_id = consignment_agreement_id
                