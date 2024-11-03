# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrPerformanceCalibration(models.Model):
    _name = 'hr.performance.calibration'
    _description = 'HR Performance Calibration'

    def _default_employee(self):
        return self.env.user.employee_id

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Char('Name')
    sequence_number = fields.Char('Sequence Number', default="New")
    evaluation_period_id = fields.Many2one('performance.date.range', string='Evaluation Period', domain=_multi_company_domain)
    select_based_on = fields.Selection([('nine_box_grid','Nine Box Grid'), ('department','Department'),
                                ('job_position','Job Position'), ('employee','Employee')], default='', string='Select Based On')
    nine_box_grid_ids = fields.Many2many('nine.box.matrix', string='Nine Box Grid')
    department_ids = fields.Many2many('hr.department', string='Department', domain=_multi_company_domain)
    job_position_ids = fields.Many2many('hr.job', string='Job Position', domain=_multi_company_domain)
    employee_ids = fields.Many2many('hr.employee', string='Employee', domain=_multi_company_domain)
    calibrator_id = fields.Many2one('hr.employee', string="Calibrator", default=_default_employee)
    state = fields.Selection([('draft', 'Draft'), ('on_process', 'On-Process'), ('calibrated', 'Calibrated')], default='draft', string='Stages')
    calibration_lines_ids = fields.One2many('hr.performance.calibration.lines','parent_id', string='Calibration Line')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrPerformanceCalibration, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrPerformanceCalibration, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.onchange('evaluation_period_id')
    def onchange_evaluation_period_id(self):
        for rec in self:
            rec.nine_box_grid_ids = [(5,0,0)]
            rec.department_ids = [(5,0,0)]
            rec.job_position_ids = [(5,0,0)]
            rec.employee_ids = [(5,0,0)]
            rec.calibration_lines_ids = [(5,0,0)]

    @api.onchange('select_based_on')
    def onchange_select_based_on(self):
        for rec in self:
            rec.nine_box_grid_ids = [(5,0,0)]
            rec.department_ids = [(5,0,0)]
            rec.job_position_ids = [(5,0,0)]
            rec.employee_ids = [(5,0,0)]
            rec.calibration_lines_ids = [(5,0,0)]

    @api.onchange('nine_box_grid_ids','evaluation_period_id')
    def onchange_nine_box_grid_ids(self):
        for rec in self:
            if rec.evaluation_period_id and rec.select_based_on == 'nine_box_grid':
                evaluation_obj = self.env['employee.performance'].search([('date_range_id','=',rec.evaluation_period_id.id),('n_grid_id','in',rec.nine_box_grid_ids.ids)])
                evaluation_list = []
                for line in evaluation_obj:
                    evaluation_list.append(line.id)
                exist_line = []
                for line in rec.calibration_lines_ids:
                    if line.evaluation_id.id not in evaluation_list:
                        rec.calibration_lines_ids = [(2, line.id)]
                    else:
                        exist_line.append(line.evaluation_id.id)
                calibration_line_list = []
                for evaluation in evaluation_obj:
                    if evaluation.id not in exist_line:
                        calibration_line_list.append([0,0,{
                                                        'evaluation_id': evaluation.id,
                                                        'employee_id': evaluation.employee_id.id,
                                                        'n_grid_id': evaluation.n_grid_id.id,
                                                        'overal_score': evaluation.overal_score
                                                        }])
                rec.write({'calibration_lines_ids': calibration_line_list})
    
    @api.onchange('department_ids','evaluation_period_id')
    def onchange_department_ids(self):
        for rec in self:
            if rec.evaluation_period_id and rec.select_based_on == 'department':
                employee_ids = self.env['hr.employee'].search([('department_id','in',rec.department_ids.ids)])
                evaluation_obj = self.env['employee.performance'].search([('date_range_id','=',rec.evaluation_period_id.id),('employee_id','in',employee_ids.ids)])
                evaluation_list = []
                for line in evaluation_obj:
                    evaluation_list.append(line.id)
                exist_line = []
                for line in rec.calibration_lines_ids:
                    if line.evaluation_id.id not in evaluation_list:
                        rec.calibration_lines_ids = [(2, line.id)]
                    else:
                        exist_line.append(line.evaluation_id.id)
                calibration_line_list = []
                for evaluation in evaluation_obj:
                    if evaluation.id not in exist_line:
                        calibration_line_list.append([0,0,{
                                                        'evaluation_id': evaluation.id,
                                                        'employee_id': evaluation.employee_id.id,
                                                        'n_grid_id': evaluation.n_grid_id.id,
                                                        'overal_score': evaluation.overal_score
                                                        }])
                rec.write({'calibration_lines_ids': calibration_line_list})
    
    @api.onchange('job_position_ids','evaluation_period_id')
    def onchange_job_position_ids(self):
        for rec in self:
            if rec.evaluation_period_id and rec.select_based_on == 'job_position':
                employee_ids = self.env['hr.employee'].search([('job_id','in',rec.job_position_ids.ids)])
                evaluation_obj = self.env['employee.performance'].search([('date_range_id','=',rec.evaluation_period_id.id),('employee_id','in',employee_ids.ids)])
                evaluation_list = []
                for line in evaluation_obj:
                    evaluation_list.append(line.id)
                exist_line = []
                for line in rec.calibration_lines_ids:
                    if line.evaluation_id.id not in evaluation_list:
                        rec.calibration_lines_ids = [(2, line.id)]
                    else:
                        exist_line.append(line.evaluation_id.id)
                calibration_line_list = []
                for evaluation in evaluation_obj:
                    if evaluation.id not in exist_line:
                        calibration_line_list.append([0,0,{
                                                        'evaluation_id': evaluation.id,
                                                        'employee_id': evaluation.employee_id.id,
                                                        'n_grid_id': evaluation.n_grid_id.id,
                                                        'overal_score': evaluation.overal_score
                                                        }])
                rec.write({'calibration_lines_ids': calibration_line_list})
    
    @api.onchange('employee_ids','evaluation_period_id')
    def onchange_employee_ids(self):
        for rec in self:
            if rec.evaluation_period_id and rec.select_based_on == 'employee':
                evaluation_obj = self.env['employee.performance'].search([('date_range_id','=',rec.evaluation_period_id.id),('employee_id','in',rec.employee_ids.ids)])
                evaluation_list = []
                for line in evaluation_obj:
                    evaluation_list.append(line.id)
                exist_line = []
                for line in rec.calibration_lines_ids:
                    if line.evaluation_id.id not in evaluation_list:
                        rec.calibration_lines_ids = [(2, line.id)]
                    else:
                        exist_line.append(line.evaluation_id.id)
                calibration_line_list = []
                for evaluation in evaluation_obj:
                    if evaluation.id not in exist_line:
                        calibration_line_list.append([0,0,{
                                                        'evaluation_id': evaluation.id,
                                                        'employee_id': evaluation.employee_id.id,
                                                        'n_grid_id': evaluation.n_grid_id.id,
                                                        'overal_score': evaluation.overal_score
                                                        }])
                rec.write({'calibration_lines_ids': calibration_line_list})


    def action_process(self):
        for rec in self:
            rec.sequence_number = self.env['ir.sequence'].next_by_code('hr.performance.calibraion')
            rec.state = 'on_process'
    
    def action_submit(self):
        for rec in self:
            for line in rec.calibration_lines_ids:
                if line.adjust_id:
                    line.evaluation_id.n_grid_adjusted_id = line.adjust_id
            rec.state = 'calibrated'

class HrPerformanceCalibrationLine(models.Model):
    _name = 'hr.performance.calibration.lines'
    _description = 'HR Performance Calibration Line'

    parent_id = fields.Many2one('hr.performance.calibration', string="Performance Calibration")
    evaluation_id = fields.Many2one('employee.performance', string="Evaluation")
    employee_id = fields.Many2one('hr.employee', string="Employee Name")
    n_grid_id = fields.Many2one('nine.box.matrix', string="Nine Box Grid")
    overal_score = fields.Float('Overal Score')
    adjust_id = fields.Many2one('nine.box.matrix', string="Adjust")
    reason = fields.Text(string="Reason")