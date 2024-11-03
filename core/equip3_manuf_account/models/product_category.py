from odoo import api, fields, models, tools, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def _default_hide_wip_account(self):
        return not self.env.company.manufacturing
    
    def _compute_hide_wip_account(self):
        for record in self:
            record.hide_wip_account = not self.env.company.manufacturing

    mrp_wip_account_id = fields.Many2one('account.account', string='Manufacturing WIP Account', tracking=True)
    hide_wip_account = fields.Boolean(default=_default_hide_wip_account, string='Hide WIP Account', compute=_compute_hide_wip_account)
