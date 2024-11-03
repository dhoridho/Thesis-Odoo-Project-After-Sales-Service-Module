from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
import json
import pytz


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    project_information_ids = fields.One2many('construction.project.information', 'employee_id', string='Project Information')

    # unused method
    # not removed to avoid issue in existing database
    def update_project_task(self):
        pass

    # Override to change attendance logic according to Construction's Labour Cost Rate needs
    def _attendance_action_change(self):
        self.ensure_one()
        action_date = fields.Datetime.now()
        location = self.env.context.get("att_location", False)
        att = self.last_attendance_id.sudo()

        tz = pytz.timezone(self.tz)
        now_tz = datetime.now().astimezone(tz)
        date_today = now_tz.date()

        schedule = self.env['employee.working.schedule.calendar'].search(
            [('employee_id', '=', self.id), ('date_start', '=', date_today)], limit=1)
        if schedule.start_checkin and schedule.end_checkout:
            checked_in_time = schedule.start_checkin <= datetime.now() <= schedule.end_checkout
            if self.attendance_state != 'checked_in' and not checked_in_time:
                raise ValidationError(_('You cannot check in now.'))

        if location:
            vals = {
                'employee_id': self.id,
            }
            if self.active_location_ids and self.selected_active_location_id:
                vals['active_location_id'] = [(4, self.selected_active_location_id.active_location_id.id)]

            self.parse_param(vals)

            HrAttendance = self.env['hr.attendance'].search(
                [('employee_id', '=', self.id), ('start_working_date', '=', date.today()),
                 ('check_in', '!=', False), ('active', '=', True), ('active_location_id', '=', self.selected_active_location_id.active_location_id.id)], limit=1)

            face_recognition_store = self.env['ir.config_parameter'].sudo(
            ).get_param('hr_attendance_face_recognition_store')
            snapshot = False
            if face_recognition_store:
                snapshot = self.env.context.get("webcam", False)
            # Considered as checkout if the employee is already checked in and the selected location is the same as the active location
            if HrAttendance and HrAttendance.active_location_id[0]._origin.id == self.selected_active_location_id.active_location_id._origin.id:
                vals['attendance_status'] = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_status') or ''
                vals.update(
                    {
                        'check_out': action_date,
                    })
                self.parse_param(vals, 'out')
                HrAttendance.write(vals)
                HrAttendance.write(
                    {
                        "check_out_latitude": location[0],
                        "check_out_longitude": location[1],
                        'face_recognition_access_check_out': snapshot,
                    }
                )
                return HrAttendance
            # Considered as checkin if the employee is not checked in or the selected location is different from the active location
            else:
                vals = {
                    'employee_id': self.id,
                    'check_in': action_date,
                }
                if self.active_location_ids and self.selected_active_location_id:
                    vals['active_location_id'] = [(4, self.selected_active_location_id.active_location_id.id)]
                self.parse_param(vals)
                attendance = self.env['hr.attendance'].create(vals)
                if attendance:
                    attendance.write(
                        {
                            "check_in_latitude": location[0],
                            "check_in_longitude": location[1],
                            'face_recognition_access_check_in': snapshot,
                        }
                    )
                    attendance.onchange_active_location_construction()
                return attendance
        else:
            raise ValidationError(_('No active location found.'))


class ConstructionProjectInformation(models.Model):
    _name = 'construction.project.information'
    _description = 'Construction Project Information'

    project_id = fields.Many2one('project.project', string='Project')
    project_task_id = fields.Many2one('project.task', string='Job Order', domain="[('labour_usage_ids', '!=', False), ('project_id', '=', project_id), ('state', '=', 'inprogress')]")
    active_location_id = fields.Many2one('project.location', string='Location')
    project_scope_id = fields.Many2one('project.scope.line', string='Scope',)
    section_id = fields.Many2one('section.line', string='Section')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Position')
    product_id = fields.Many2one('product.product', string='Position')
    name = fields.Char(string='Name', compute='_compute_name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    active_location_domain_dump = fields.Char(string='Active Location Domain', compute='_compute_active_location_domain_dump')
    project_scope_domain_dump = fields.Char(string='Project Scope Domain', compute='_compute_project_scope_domain_dump')
    section_domain_dump = fields.Char(string='Section Domain', compute='_compute_section_domain_dump')
    group_of_product_domain_dump = fields.Char(string='Group of Product Domain', compute='_compute_group_of_product_domain_dump')
    product_domain_dump = fields.Char(string='Product Domain', compute='_compute_product_domain_dump')
    uom_id = fields.Many2one('uom.uom', string='Periodic')
    rate_amount = fields.Float(string='Rate')
    labour_cost_rate_id = fields.Many2one('labour.cost.rate', string='Labour Cost Rate')
    rate_periodic = fields.Selection(related='labour_cost_rate_id.rate_periodic', string='Periodic')

    @api.depends('project_task_id')
    def _compute_active_location_domain_dump(self):
        for rec in self:
            if rec.project_task_id:
                rec.active_location_domain_dump = json.dumps([('id', 'in', rec.project_task_id.active_location_ids.ids)])
            else:
                rec.active_location_domain_dump = json.dumps([('id', 'in', False)])

    @api.depends('project_task_id', 'active_location_id')
    def _compute_project_scope_domain_dump(self):
        for rec in self:
            if rec.project_task_id and rec.active_location_id:
                rec.project_scope_domain_dump = json.dumps([('id', 'in', rec.project_task_id.labour_usage_ids.project_scope_id.ids)])
            else:
                rec.project_scope_domain_dump = json.dumps([('id', 'in', False)])

    @api.depends('project_scope_id')
    def _compute_section_domain_dump(self):
        for rec in self:
            if rec.project_scope_id:
                labour_section = []
                for labour in rec.project_task_id.labour_usage_ids:
                    if labour.project_scope_id.id == rec.project_scope_id._origin.id:
                        labour_section.append(labour.section_id.id)
                rec.section_domain_dump = json.dumps([('id', 'in', labour_section)])
            else:
                rec.section_domain_dump = json.dumps([('id', 'in', False)])

    @api.depends('section_id')
    def _compute_group_of_product_domain_dump(self):
        for rec in self:
            if rec.section_id:
                labour_group_of_product = []
                for labour in rec.project_task_id.labour_usage_ids:
                    if labour.section_id.id == rec.section_id._origin.id:
                        labour_group_of_product.append(labour.group_of_product_id.id)
                rec.group_of_product_domain_dump = json.dumps([('id', 'in', labour_group_of_product)])
            else:
                rec.group_of_product_domain_dump = json.dumps([('id', 'in', False)])

    @api.depends('group_of_product_id')
    def _compute_product_domain_dump(self):
        for rec in self:
            if rec.group_of_product_id:
                labour_product = []
                for labour in rec.project_task_id.labour_usage_ids:
                    if labour.group_of_product_id.id == rec.group_of_product_id._origin.id:
                        labour_product.append(labour.product_id.id)
                rec.product_domain_dump = json.dumps([('id', 'in', labour_product)])
            else:
                rec.product_domain_dump = json.dumps([('id', 'in', False)])

    @api.depends('project_id', 'project_task_id', 'active_location_id', 'project_scope_id', 'section_id', 'group_of_product_id', 'product_id')
    def _compute_name(self):
        for rec in self:
            if rec.project_id and rec.project_task_id and rec.active_location_id and rec.project_scope_id and rec.section_id and rec.group_of_product_id and rec.product_id:
                rec.name = rec.project_id.name + ' - ' + rec.project_task_id.name + ' - ' + rec.active_location_id.name + ' - ' + rec.project_scope_id.name + ' - ' + rec.section_id.name + ' - ' + rec.group_of_product_id.name + ' - ' + rec.product_id.name
            else:
                rec.name = ''
