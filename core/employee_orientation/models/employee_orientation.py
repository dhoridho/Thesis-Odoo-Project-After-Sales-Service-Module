# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Anusha @cybrosys(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from lxml import etree


class Orientation(models.Model):
    _name = 'employee.orientation'
    _description = "Employee Orientation"
    _inherit = 'mail.thread'
    
    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    name = fields.Char(string='Employee Orientation', readonly=True, default=lambda self: _('New'))
    employee_name = fields.Many2one('hr.employee', string='Employee', required=True,default=_default_employee_id)
    department = fields.Many2one('hr.department', string='Department', related='employee_name.department_id',
                                 required=True)
    date = fields.Datetime(string="Date")
    # date = fields.Datetime.to_string(dateText)
    responsible_user = fields.Many2one('res.users', string='Responsible User')
    employee_company = fields.Many2one('res.company', string='Company', required=True,
                                       default=lambda self: self.env.company.id)
    parent_id = fields.Many2one('hr.employee', string='Manager', related='employee_name.parent_id')
    job_id = fields.Many2one('hr.job', string='Job Title', related='employee_name.job_id',
                             domain="[('department_id', '=', department)]")
    orientation_id = fields.Many2one('orientation.checklist', string='Orientation Checklist',
                                     domain="[('checklist_department','=', department)]", required=True)
    note_id = fields.Text('Description')
    orientation_request = fields.One2many('orientation.request', 'request_orientation', string='Orientation Request')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Canceled'),
        ('complete', 'Completed'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    employee_domain_ids = fields.Many2many('hr.employee',string="Employee Domain",compute='_get_employee_domain_ids')
    
    
    @api.depends('employee_name')
    def _get_employee_domain_ids(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
                employee_ids = []
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                record.employee_domain_ids = employee_ids
            else:
                employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                employee_ids = []
                if employee:
                    for record_employee in employee:
                        employee_ids.append(record_employee.id)
                record.employee_domain_ids = employee_ids
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Orientation, self).fields_view_get(
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
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'false')
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
        views = [(self.env.ref('employee_orientation.view_employee_orientation_tree').id,'tree'),
                 (self.env.ref('employee_orientation.view_employee_orientation_form').id,'form')]
        search_view_id = self.env.ref('employee_orientation.view_employee_orientation_search').id
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Orientation',
                'res_model': 'employee.orientation',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
                'domain': [('employee_name.user_id', '=', self.env.user.id)]
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Orientation',
                'res_model': 'employee.orientation',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
            }

    def confirm_orientation(self):
        self.write({'state': 'confirm'})
        for values in self.orientation_id.checklist_line_id:
            self.env['orientation.request'].create({
                'request_name': values.line_name,
                'request_orientation': self.id,
                'partner_id': values.responsible_user.id,
                'request_date': self.date,
                'employee_id': self.employee_name.id,
            })

    def cancel_orientation(self):
        for request in self.orientation_request:
            request.state = 'cancel'
        self.write({'state': 'cancel'})

    def complete_orientation(self):
        force_complete = False
        for request in self.orientation_request:
            if request.state == 'new':
                force_complete = True
        if force_complete:
            print("==================forced if ================")
            return {
                'name': 'Complete Orientation',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'orientation.force.complete',
                'type': 'ir.actions.act_window',
                'context': {'default_orientation_id': self.id},
                'target': 'new',
            }
        self.write({'state': 'complete'})

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.orientation')
        result = super(Orientation, self).create(vals)
        return result
