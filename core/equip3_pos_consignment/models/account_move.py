# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_order_line_ids = fields.Many2many(
        'pos.order.line',
        string="POS Order Line",
        readonly=True,
        copy=False,
    )


    def unlink(self):
        #TODO: update Billed Consignment at pos.order.line
        account_move_ids = []
        for rec in self:
            if rec.consignment_id:
                account_move_ids += [rec.id]

        domain = [('consignment_id','!=', False), ('id', 'in', account_move_ids), ('state','=','draft')]
        moves = self.env['account.move'].search(domain)
        for move in moves:
            for line in move.pos_order_line_ids:
                line.write({'is_billed_consignment': False})
                
        return super().unlink()