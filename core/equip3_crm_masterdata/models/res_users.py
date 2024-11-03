from odoo import models, fields, api, _
from odoo.tools import lazy_property
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        check = False
        group_manage_crm = self.env.ref("equip3_crm_masterdata.group_manage_crm")
        if 'in_group_%s' % group_manage_crm.id in vals:
            check = True
            is_group_manage_crm = vals['in_group_%s' % group_manage_crm.id]
            if not self.env.user.has_group("base.group_system"):
                raise ValidationError("Only administrator can edit settings")
        res = super().write(vals)
        if check:
            try:
                access_management = self.env.ref('equip3_crm_masterdata.access_management_manage_crm')
            except:
                access_management = False
            if access_management:
                if is_group_manage_crm and self.id in access_management.user_ids.ids:
                    access_management.user_ids = [(3, self.id)]
                elif not is_group_manage_crm and self.id not in access_management.user_ids.ids:
                    access_management.user_ids = [(4, self.id)]
        return res