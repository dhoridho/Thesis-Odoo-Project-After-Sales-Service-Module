# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta

class IncidentReport(models.Model):
    _name = 'incident.report.employee'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Incident report'
    _check_company_auto = True
    _order = 'date_of_accident DESC'
    
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    date_of_accident = fields.Datetime(string='Date of Accident', required=True)
    incident_category_id = fields.Many2one('incident.category','Incident Category', required=True)
    description = fields.Text('Incident Description', required=True)
    impact = fields.Text('Impact / Injury to Subject')
    action = fields.Text('Immediate Action Taken')
    emerg_notified = fields.Boolean('Notified to emergency contact')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('investigation', 'On Investigation'),
        ('resolve', 'Resolved'),
        ('unresolve', 'Unresolved'),
        ('cancel', 'cancelled')], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    death_report = fields.Boolean(string='Death Report', default=False)
    type = fields.Selection([
        ('incident', 'Incident Report'),
        ('death', 'Death Report')], string='type', store=True, default='incident')
    total_investigation_report = fields.Integer(string="Investigation Report",compute='_comute_count_investigation_report')
    multiple_incident_id = fields.Many2one('incident.report.multiple')
    is_new = fields.Boolean(string='Is New', default=True)

    @api.onchange('date_of_accident')
    def depends_date_of_accident(self):
        for res in self:
            current_date = datetime.now()
            if res.date_of_accident:
                if res.date_of_accident > current_date:
                    raise ValidationError("Can not input more than the current time.")

    @api.model
    def create(self, vals):
        if not vals.get('death_report'):
            vals['name'] = self.env['ir.sequence'].next_by_code('incident.report.employee.sequence')
            vals['type'] = 'incident'
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('death.report.employee.sequence')
            vals['type'] = 'death'
        return super(IncidentReport, self).create(vals)

    def _comute_count_investigation_report(self):
        for rec in self:
            investigation_report_count = self.env['investigation.report.employee'].search_count([('employee_incident_id','=',rec.id)])
            rec.total_investigation_report = investigation_report_count

    @api.onchange('multiple_incident_id.date_of_accident', 'multiple_incident_id.incident_category_id', 'multiple_incident_id.description', 'multiple_incident_id.branch_id', 'date_of_accident', 'branch_id')
    def depends_date_accident(self):
        for res in self:
            if res.multiple_incident_id:
                res.date_of_accident = res.multiple_incident_id.date_of_accident
                res.branch_id = res.multiple_incident_id.branch_id.id
                res.incident_category_id = res.multiple_incident_id.incident_category_id.id
                res.description = res.multiple_incident_id.description

    @api.onchange('date_of_accident')
    def _onchange_date_of_accident(self):
        for rec in self:
            if rec.employee_id.id:
                employee_attendance = rec.env['hr.attendance'].search([('employee_id', '=', rec.employee_id.id)])
                is_valid = True
                if len(employee_attendance) > 0:
                    if rec.date_of_accident:
                        date_of_accident = rec.date_of_accident
                        incident_work_hours = (employee_attendance.
                                               search([('start_working_date', '=', date_of_accident.date())]))
                        if len(incident_work_hours) > 0:
                            for work_hour in incident_work_hours:
                                if work_hour.start_working_date == date.today():
                                    if not work_hour.check_out:
                                        if not work_hour.check_in < date_of_accident <= datetime.now():
                                            is_valid = False
                                    else:
                                        if not work_hour.check_in < date_of_accident <= work_hour.check_out:
                                            is_valid = False
                                else:
                                    if not work_hour.check_out:
                                        if not work_hour.check_in < date_of_accident <= work_hour.check_in.replace(hour=23,
                                                                                                                   minute=59,
                                                                                                                   second=59):
                                            is_valid = False
                                    else:
                                        if not work_hour.check_in < date_of_accident <= work_hour.check_out:
                                            is_valid = False
                        else:
                            is_valid = False
                else:
                    is_valid = False

                if not is_valid:
                    raise ValidationError("Date of accident should inside attendance hours.")
    
    #Button
    def action_view_investigation_report(self):
        return {
            'name': ("Investigation Report"),
            'view_mode': 'tree,form',
            'res_model': 'investigation.report.employee',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('employee_incident_id','=',self.id)],
        }
    
    def investigation(self):
        for res in self:
            if res.multiple_incident_id:
                multiple = res.multiple_incident_id
                if multiple.state != 'confirm':
                    raise ValidationError("Can't continue this process, please confirm the multiple incident first!")
                else:
                    res.write({'state': 'investigation'})
            else:
                res.write({'state': 'investigation'})
            
    def create_investigation(self):
        for record in self:
            context = {
                'default_branch_id': record.branch_id.id,
                'default_employee_id': record.employee_id.id,
                'default_employee_incident_id': record.id,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Investigation Report',
                'view_mode': 'form',
                'res_model': 'investigation.report.employee',
                'target': 'current',
                'context': context,
            }
            
    def resolve(self):
        for res in self:
            if res.multiple_incident_id:
                multiple = res.multiple_incident_id
                if multiple.state != 'confirm':
                    raise ValidationError("Can't continue this process, please confirm the multiple incident first!")
                else:
                    res.write({'state': 'resolve'})
            else:
                res.write({'state': 'resolve'})
            
    def unresolve(self):
        for res in self:
            if res.multiple_incident_id:
                multiple = res.multiple_incident_id
                if multiple.state != 'confirm':
                    raise ValidationError("Can't continue this process, please confirm the multiple incident first!")
                else:
                    res.write({'state': 'unresolve'})
            else:
                res.write({'state': 'unresolve'})

    def cancel_investigation(self):
        for res in self:
            res.write({'state': 'cancel'})

    def reinvestigate(self):
        for res in self:
            res.write({'state': 'investigation'})