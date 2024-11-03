from odoo import models,api
from lxml import etree



class EmployeePerformanceInherit(models.Model):
    _inherit = 'employee.performance'
    
    
    def custom_menu(self):
        search_view_id = self.env.ref('equip3_hr_employee_appraisals.employee_performance_search').id
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'All Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form',
                'search_view_id': search_view_id,
                'domain':[('employee_id','in',employee_ids)],
                'context': {'search_default_group_performance_planning':1}
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'All Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form',
                'search_view_id': search_view_id,
                'context': {'search_default_group_performance_planning':1}
                }
            
    def custom_menu_self_evaluation(self):
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_self_service') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            # employee_ids = []
            # my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            # if my_employee:
            #         for child_record in my_employee.child_ids:
            #             employee_ids.append(my_employee.id)
            #             employee_ids.append(child_record.id)
            #             child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Self Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form',
                'domain':[('employee_id','=',self.env.user.employee_id.id)]
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Self Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form'
                }
            
    def custom_menu_manager_evaluation(self):
        search_view_id = self.env.ref('equip3_hr_employee_appraisals.employee_performance_search').id
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Manager Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form',
                'search_view_id': search_view_id,
                'domain':[('employee_id','in',employee_ids)],
                'context': {'search_default_group_performance_planning':1}
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Manager Evaluation',
                'res_model': 'employee.performance',
                'view_mode': 'tree,form',
                'search_view_id': search_view_id,
                'context': {'search_default_group_performance_planning':1}
                }
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(EmployeePerformanceInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        root.set('create', 'false')
        root.set('edit', 'true')
        root.set('delete', 'false')
        res['arch'] = etree.tostring(root)
            
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeePerformanceInherit, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeePerformanceInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)