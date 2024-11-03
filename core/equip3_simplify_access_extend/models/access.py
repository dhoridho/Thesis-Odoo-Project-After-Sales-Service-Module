from odoo import fields, models, api, _
from odoo.exceptions import UserError


class access_management(models.Model):
    _inherit = 'access.management'

    @api.onchange('apply_by_group')
    def _onchange_apply_by_group(self):
        for record in self:
            record.access_group_ids = False
            record.access_res_group_ids = False
        self.onchange_access_group_ids()
        self.onchange_res_access_group_ids()
            

    @api.onchange('access_group_ids')
    def onchange_access_group_ids(self):
        for rec in self:
            rec.user_ids  = False
            rec.user_ids = rec.access_group_ids.mapped('user_ids')



    @api.onchange('access_res_group_ids')
    def onchange_res_access_group_ids(self):
        for rec in self:
            rec.user_ids  = False
            users = rec.access_res_group_ids.mapped('users')
            users |= rec.user_ids
            rec.user_ids = users



