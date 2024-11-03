from odoo import models, fields, api, _


class MrpProductionWizardLine(models.TransientModel):
    _inherit = 'mrp.production.wizard.line'
    
    def _prepare_order_values(self, bom_id, product_id, product_qty, uom_id, parent_id):
        res = super(MrpProductionWizardLine, self)._prepare_order_values(bom_id, product_id, product_qty, uom_id, parent_id)
        bom = self.env['mrp.bom'].browse(bom_id)
        res['rejected_product_id'] = bom.rejected_product_id.id
        return res
