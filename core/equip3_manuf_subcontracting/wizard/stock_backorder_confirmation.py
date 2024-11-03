from odoo import models


class StockBackorderConfirm(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'
    
    def process_cancel_backorder(self):
        res = super(StockBackorderConfirm, self).process_cancel_backorder()
        if self.pick_ids:
            for picking in self.pick_ids:
                if picking.subcon_production_id:
                    search_mor = self.env['mrp.production'].search([('id', '=', picking.subcon_production_id.id)], limit=1)
                    for line_wo in search_mor.workorder_ids:
                        if line_wo.state == 'ready' or line_wo.state == 'pause':
                            line_wo.button_start()
                            line_wo.button_finish()
                        elif line_wo.state == 'progress':
                            line_wo.button_finish()
                        if line_wo.consumption_ids:
                            for consumption in line_wo.consumption_ids:
                                if consumption.state != 'confirm':
                                    consumption.unlink()
        return res
