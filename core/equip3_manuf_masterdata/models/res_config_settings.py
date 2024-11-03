from odoo import models, api, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bom_tools = fields.Boolean(string='Tools', related='company_id.bom_tools', readonly=False)

    @api.model
    def create(self, vals):
        vals.update({'group_mrp_routings': True, 'module_mrp_workorder': True})
        return super(ResConfigSettings, self).create(vals)
