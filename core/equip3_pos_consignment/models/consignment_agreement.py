# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError

class ConsignmentAgreement(models.Model):
    _inherit = 'consignment.agreement'


    pos_order_line_count = fields.Integer('POS Order Line Count', compute='_compute_pos_order_line_count')


    def get_pos_order_line_from_consignment(self):
        self.ensure_one()
        res_ids = []

        self.env.cr.execute('''
            SELECT 
                spl.name
            FROM stock_move_line AS sml 
            INNER JOIN stock_move AS sm ON sm.id = sml.move_id
            INNER JOIN stock_picking AS sp ON sp.id = sm.picking_id
            INNER JOIN stock_production_lot AS spl ON spl.id = sml.lot_id
            WHERE  sml.lot_id IS NOT NULL
                AND sp.consignment_id = {consignment_id}
            GROUP BY spl.name
        '''.format(consignment_id=self.id))
        lots_names = [x[0] for x in self.env.cr.fetchall()]

        #TODO: Get pos.order.line ids by lot/serial number
        if lots_names:
            query = '''
                SELECT 
                    array_agg(pol.id)
                FROM pos_order_line AS pol 
                INNER JOIN pos_pack_operation_lot AS ppol ON ppol.pos_order_line_id = pol.id    
                WHERE ppol.lot_name IN ({lots_names})
            '''.format(lots_names=str(lots_names)[1:-1])
            self.env.cr.execute(query)
            result = self.env.cr.fetchone()
            if result and result[0] != None:
                res_ids += result[0]


        #TODO: Get from stock.valuation.layer
        query = '''
            SELECT 
                array_agg(pol.id)
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
                AND svl.consignment_id = {consignment_id}
        '''.format(consignment_id=self.id)
        self._cr.execute(query)
        result = self.env.cr.fetchone()
        if result and result[0] != None:
            res_ids += result[0]

        return res_ids

    def _compute_pos_order_line_count(self):
        for rec in self:
            pos_order_line_ids = rec.get_pos_order_line_from_consignment()
            domain = [('id', 'in', pos_order_line_ids)]
            rec.pos_order_line_count = self.env['pos.order.line'].search_count(domain)

    def action_view_pos_order_line(self):
        self.ensure_one()
        pos_order_line_ids = self.get_pos_order_line_from_consignment()
        context = dict(self._context, create=False)
        context['tree_view_ref'] = 'equip3_pos_consignment.consignment_pos_order_line_view_tree'
        return {
            'name': _('POS Order Line'),
            'view_mode': 'tree',
            'res_model': 'pos.order.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', pos_order_line_ids)],
            'context': context
        }
 

class ConsignmentAgreementLine(models.Model):
    _inherit = 'consignment.agreement.line'

    # OVERIDE: equip3_inventory_consignment
    def get_billed_qty(self):
        for rec in self:
            account_moves = self.env['account.move'].search([('consignment_id', '=', rec.consignment_id.id)])
            rec.billed_quantities = 0
            if rec.consignment_id and account_moves:
                for move in account_moves:
                    if move.sale_order_line_ids:
                        for so in move.sale_order_line_ids:
                            if rec.product_id.id == so.product_id.id:
                                rec.billed_quantities += so.qty_delivered

                    for line in move.pos_order_line_ids:
                        if rec.product_id.id == line.product_id.id:
                            rec.billed_quantities += line.qty 