
from odoo import api, fields, models, _


class MultipleRfq(models.TransientModel):
    _inherit = 'multiple.rfq'
        
    @api.onchange('vendor_ids')
    def _onchange_vendor_ids(self):
        context = dict(self.env.context) or {}
        res = super(MultipleRfq, self)._onchange_vendor_ids()
        if context.get('assets_orders'):
            return {'domain': {'product_ids': [('type', '=','asset')]}}
        return res 
    
