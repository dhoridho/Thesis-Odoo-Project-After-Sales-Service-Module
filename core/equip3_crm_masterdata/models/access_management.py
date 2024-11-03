from odoo import models, fields, api, _
from odoo.tools import lazy_property
from odoo.exceptions import ValidationError


class access_management(models.Model):
    _inherit = "access.management"

    @api.model
    def create(self, vals):
        # add all users for access management from data
        if vals['name'] == 'Manage CRM':
            try:
                access_crm = self.env.ref('equip3_crm_masterdata.access_management_manage_crm')
            except:
                access_crm = False
            if not access_crm:
                user_ids = []
                all_user_ids = self.env['res.users'].search([('share','=',False)])
                for i in all_user_ids:
                    if not i.has_group("equip3_crm_masterdata.group_manage_crm"):
                        user_ids.append(i.id)
                vals['user_ids'] = [(6, 0, user_ids)]
        res = super().create(vals)
        return res