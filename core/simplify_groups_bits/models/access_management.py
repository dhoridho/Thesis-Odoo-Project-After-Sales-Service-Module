from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class access_management(models.Model):
    _inherit = "access.management"

    apply_by_group = fields.Boolean('Apply By Group')
    access_group_ids = fields.Many2many('access.group', 'access_group_access_management_rel_bits',
                                        'access_management_id', 'access_group_id', string='Access Groups')
    access_res_group_ids = fields.Many2many('res.groups', 'access_group_res_group_rel_bits',
                                        'access_management_id', 'res_group_id', string='Access Groups')
    

    



