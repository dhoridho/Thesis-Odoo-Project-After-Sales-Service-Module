from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.constrains('location_dest_id','branch_id')
    def _location_and_branch(self):
        context = dict(self.env.context)
        for record in self:
            if record.branch_id:
                if record.location_dest_id.usage != 'supplier':
                    # if record.branch_id.id != record.location_dest_id.warehouse_id.branch_id.id and record.state == 'draft' and context.get('picking_type_code') == 'incoming':
                    if record.branch_id.id != record.location_dest_id.warehouse_id.branch_id.id and record.state == 'draft' and record.picking_type_code == 'incoming':
                        raise ValidationError(
                        _('User are not allowed access' ' %s ' 'under this' ' %s ', record.location_dest_id.name, record.branch_id.name))
                    else:
                        pass
                else:
                    pass
            else:
                pass
