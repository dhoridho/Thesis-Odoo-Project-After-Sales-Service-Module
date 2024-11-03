from odoo import models, fields, api, _
from odoo.osv import expression
from lxml import etree
# import sys

# sys.setrecursionlimit(200)


class HrEmployeeRoleInherit(models.Model):
    _inherit = 'hr.employee'
    is_readonly_self_service = fields.Boolean(compute='_get_self_service')
    
    
    
    @api.depends('create_date')
    def _get_self_service(self):
        for record in self:
            if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
                record.is_readonly_self_service = True
            else:
                record.is_readonly_self_service = False
                
            
    def _get_amployee_hierarchy(self,employee_ids,child_ids,employee_id):
        for data_employee in child_ids.filtered(lambda line:line.id != employee_id):
            employee_ids.append(data_employee.id)
            if data_employee.child_ids:
                self._get_amployee_hierarchy(employee_ids,data_employee.child_ids,data_employee.id)

            
        
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrEmployeeRoleInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        

        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager') or self.env.user.has_group('hr_attendance.group_hr_attendance_manager') :
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
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employees',
                'res_model': 'hr.employee',
                'view_type': 'form',
                'view_mode': 'kanban,tree,form',
                'domain': [('user_id', '=', self.env.user.id)]
            }
        elif  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            employee_ids = []
            my_employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
            if my_employee:
                employee_ids.append(my_employee.id)
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    self._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employees',
                'res_model': 'hr.employee',
                'view_type': 'form',
                'view_mode': 'kanban,tree,form',
                'domain': [('id', 'in', employee_ids)]
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employees',
                'res_model': 'hr.employee',
                'view_type': 'form',
                'view_mode': 'kanban,tree,form',
            }


