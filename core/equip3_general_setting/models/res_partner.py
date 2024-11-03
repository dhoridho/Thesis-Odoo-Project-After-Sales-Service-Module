from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, default_fields):
        "" "Add the branch of the parent as default if we are creating a child partner """
        values = super().default_get(default_fields)
        parent = self.env['res.partner']
        if 'parent_id' in default_fields and values.get('parent_id'):
            parent = self.browse(values.get('parent_id'))
            values['branch_id'] = parent.branch_id.id
        return values
