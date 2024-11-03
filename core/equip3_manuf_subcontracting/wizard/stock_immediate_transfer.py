from odoo import models


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        context = dict(self.env.context)
        force_active_model = context.get('force_active_model')
        force_active_ids = context.get('force_active_ids')
        if force_active_model and force_active_ids:
            force_active_id = force_active_ids[0]
            context.update({
                'active_model': force_active_model,
                'active_id': force_active_id,
                'active_ids': force_active_ids
            })
        self = self.with_context(context)
        return super(StockImmediateTransfer, self).process()
