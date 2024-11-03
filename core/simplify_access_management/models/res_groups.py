from odoo import fields, models, api, _
from odoo.exceptions import Warning

class res_groups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        if self.id == self.env.ref('simplify_access_management.group_read_only_ah').id:
            userchnage = vals.get('users')
            if userchnage:
                if 2 in userchnage[0][2]:
                    raise Warning(_('Admin user can not be set as a read-only..!'))
        return super(res_groups, self).write(vals)
