from odoo import fields,models,api
from lxml import etree
class equip3EmployeeMaritalStatus(models.Model):
    _name = 'employee.marital.status'
    _inherit = ['mail.thread','mail.activity.mixin']
    name = fields.Char()
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(equip3EmployeeMaritalStatus, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            if 'state' in res['fields']:
                res['fields']['state']['readonly'] = True
            
        return res
