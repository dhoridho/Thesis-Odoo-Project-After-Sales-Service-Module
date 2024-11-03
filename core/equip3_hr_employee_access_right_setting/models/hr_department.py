from odoo import models, fields, api, _
from odoo.osv import expression
from lxml import etree


class HrDepartmenttInheritEquip3HrEmployee(models.Model):
    _inherit = 'hr.department'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HrDepartmenttInheritEquip3HrEmployee, self).fields_view_get(
            view_id=view_id, view_type=view_type)

        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
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
        return res
    
    
    
    def custom_menu(self):
        search_view_id = self.env.ref("hr.view_department_filter")
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Department',
                'res_model': 'hr.department',
                'view_mode': 'tree,form',
                'search_view_id':search_view_id.id,
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Department',
                'res_model': 'hr.department',
                'view_mode': 'tree,form,kanban',
                'search_view_id':search_view_id.id,
                
            }