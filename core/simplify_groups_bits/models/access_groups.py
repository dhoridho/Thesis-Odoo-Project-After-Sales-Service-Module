from odoo import fields, models, api, _



class access_group(models.Model):
    _name = 'access.group'
    _description = "Access Group"

    name = fields.Char('Name')
    user_ids = fields.Many2many('res.users', 'access_group_user_rel_bits', 'access_group_id', 'user_id', string='Users')
    access_management_ids = fields.Many2many('access.management', 'access_group_access_management_rel_bits',
                                             'access_group_id', 'access_management_id',
                                             string='Access Management Rules')

    def write(self, vals):
        obj = self.access_management_ids

        if vals.get('access_management_ids'):
            for rec in self.access_management_ids:
                rec.user_ids = False

        res = super(access_group, self).write(vals)
        obj += self.access_management_ids
        for rec in obj:
            rec.apply_by_group = True
            rec.onchange_access_group_ids()
        return res
