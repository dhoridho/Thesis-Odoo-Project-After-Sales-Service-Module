from odoo import api, fields, models, _


class AftersalesResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_service_approval_matrix = fields.Boolean(
        config_parameter="equip3_aftersales_operation.sale_service_approval_matrix"
    )

    def write(self, vals):
        result = super(AftersalesResConfigSettings, self).write(vals) 

        group = self.env.ref('equip3_aftersales_operation.group_approval_matrix_visible')
        for record in self:
            if record.sale_service_approval_matrix:
                self.env.user.write({'groups_id': [(4, group.id)]})
            else:
                self.env.user.write({'groups_id': [(3, group.id)]})

        return result