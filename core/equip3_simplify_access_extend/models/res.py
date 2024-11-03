from odoo import fields, models, api, _


class ResGroups(models.Model):
    _inherit = "res.groups"

    
    @api.model
    def create(self, vals):
        result = super(ResGroups, self).create(vals)
        result._update_access_management()
        return result


    def write(self, vals):
        res = super(ResGroups, self).write(vals)
        if vals.get('users'):
            self._update_access_management()
        return res

    def _update_access_management(self):
        for data in self:
            access_management_obj = self.env['access.management']
            access_managements = access_management_obj.sudo().with_context(active_test=False).search([('access_res_group_ids.id','=',data.id)])
            if data.users:
                for am in access_managements:
                    users = data.users
                    users |= am.user_ids
                    am.user_ids = users



class ResUsers(models.Model):
    _inherit = "res.users"

    
    @api.model
    def create(self, vals):
        access_management_obj = self.env['access.management']
        result = super(ResUsers, self).create(vals)
        access_managements = access_management_obj.sudo().with_context(active_test=False).search([('is_all_users','=',True)])
        for access_management in access_managements:
            if result.id not in access_management.user_ids.ids:
                access_management.write({'user_ids':[(4, result.id)]})
        result._update_access_management(result.groups_id)
        return result


    def write(self, vals):
        groups_obj = self.env['res.groups']
        res = super(ResUsers, self).write(vals)
        new_vals = self._remove_reified_groups(vals)
        if new_vals.get('groups_id'):
            groups = groups_obj
            for arr_group in new_vals['groups_id']:
                if arr_group[0] == 4:
                    groups|= groups_obj.browse(arr_group[1])
                if arr_group[0] == 6:
                    for g_id in arr_group[2]:
                        groups|= groups_obj.browse(g_id)
            self._update_access_management(groups)
        return res

    def _update_access_management(self,groups=False):
        if groups:
            groups._update_access_management()