from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"


    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for record in self:
            if record.picking_type_code == 'incoming':
                account_moves = self.env['account.move'].search([('ref','ilike',record.name)])
                for move in account_moves:
                    move.write({'is_from_receiving_note': True})

        return res