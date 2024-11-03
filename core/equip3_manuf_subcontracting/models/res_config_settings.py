from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_subcontracting = fields.Boolean(related='company_id.use_subcontracting', readonly=False)

    @api.onchange('use_subcontracting')
    def _onchange_use_subcontracting(self):
        if self.use_subcontracting:
            self.is_product_service_operation_delivery = True
