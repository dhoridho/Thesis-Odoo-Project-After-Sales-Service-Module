from odoo import models, fields, api, _


class ModuleName(models.Model):
    _inherit = 'account.move'
    
    work_order_id = fields.Many2one('maintenance.work.order')
    repair_order_id = fields.Many2one('maintenance.repair.order')
    
    def action_cancel(self):
        for move in self:
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'cancel'})
        return True
