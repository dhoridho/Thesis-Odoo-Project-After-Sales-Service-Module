from odoo import _, api, fields, models


class AccessRightsProfile(models.Model):
    _name = 'access.rights.profile'
    _description = 'Access Rights Profile'

    name = fields.Char(string='Group Name')
    group_ids = fields.Many2many('res.groups', string='Groups')

    def write(self, vals):
        res = super(AccessRightsProfile, self).write(vals)
        if 'group_ids' in vals:
            user_ids = self.env['res.users'].search([
                ('access_rights_profile_id', '=', self.id)
            ])
            if user_ids:
                for user in user_ids:
                    user.write({'access_rights_profile_id': self.id})
        return res
