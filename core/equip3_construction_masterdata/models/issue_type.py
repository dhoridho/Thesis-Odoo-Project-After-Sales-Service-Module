from odoo import api, fields, models, _
from lxml import etree

class ProjectIssue(models.Model):
    _inherit = 'issue.type'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectIssue, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        return res

