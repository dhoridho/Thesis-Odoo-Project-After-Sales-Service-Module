# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import fields, models, api
from lxml import etree

class Probation(models.Model):
    _name = 'employee.probation'
    _description = 'Probation Details of an Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(Probation, self).fields_view_get(
            view_id=view_id, view_type=view_type)
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
            
        return res
    
    
    def custom_menu(self):
        views = [(self.env.ref('dev_employee_probation.tree_dev_employee_probation').id,'tree'),
                 (self.env.ref('dev_employee_probation.form_dev_employee_probation').id,'form')]
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Probation',
                'res_model': 'employee.probation',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'help':"""<p class="o_view_nocontent_smiling_face">Create Employee Probation.</p>
            """
            }
        else:
            return {
               'type': 'ir.actions.act_window',
                'name': 'Employee Probation',
                'res_model': 'employee.probation',
                'view_mode': 'tree,form',
                'views':views,
                'help':"""<p class="o_view_nocontent_smiling_face">Create Employee Probation.</p>
            """
            }

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.probation.sequence') or 'New'
        return super(Probation, self).create(vals)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id and self.employee_id.department_id and self.employee_id.department_id.id or False
            self.employee_email = self.employee_id.work_email or ''
            self.manager_id = self.employee_id.parent_id and self.employee_id.parent_id.id or False

    @api.returns('self')
    def _get_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    @api.returns('self')
    def _get_company(self):
        # company_id = False
        # employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        # if employee_id and employee_id.company_id:
        #     company_id = employee_id.company_id
        # if not company_id:
        #     company_id = self.env.user.company_id
        company_id = self.env.company
        return company_id

    name = fields.Char(string='Name', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, default=_get_employee, required=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=_get_company)
    employee_email = fields.Char(string='Email', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    review_ids = fields.One2many('probation.review', 'probation_id', string='Reviews')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: