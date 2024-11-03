from odoo import models,fields,api

class careerTransitionGeneral(models.Model):
    _name = 'career.transition.general'
    
    name = fields.Char()
    employee_id = fields.Many2one('hr.employee', domain=[('contract_id.state', '=', 'open')])
    career_transition = fields.Selection([('movement','Movement'),('termination','Termination')])
    transition_date = fields.Date()
    reason = fields.Text()
    state = fields.Selection([('draft','Draft'),('approved','Approved')],default='draft')
    id_employee = fields.Char()
    contract_id = fields.Many2one('hr.contract')
    work_location = fields.Char()
    department_id = fields.Many2one('hr.department')
    job_id = fields.Many2one('hr.job')
    new_contract = fields.Char('New Contract')
    new_contract_type_id = fields.Many2one('hr.contract.type', string='Contract Type')
    new_work_location = fields.Char('New Work Location')
    new_department_id = fields.Many2one('hr.department', string='New Department')
    new_job_id = fields.Many2one('hr.job', string='New Job Position')
    is_hide_renew = fields.Boolean('Is Hide Renew')
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for data in self:
            if data.employee_id:
                data.id_employee =  data.employee_id.employee_id
                data.work_location =  data.employee_id.work_location
                data.department_id =  data.employee_id.department_id.id
                data.job_id =  data.employee_id.job_id.id
                data.contract_id =  data.employee_id.contract_id.id
    
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('career.transition.general')
        res = super(careerTransitionGeneral, self).create(vals)
        return res
    
    def approve(self):
        for data in self:
            data.state = 'approved'
    
    def renew_contract(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Contract',
            'res_model': 'hr.contract',
            'view_type': 'form',
            'view_id': False,
            'target':'new',
            'view_mode': 'form',
            'context':{
                'default_name': self.new_contract,
                'default_employee_id': self.employee_id.id,
                'default_type_id': self.new_contract_type_id.id,
                'default_job_id': self.new_job_id.id,
                'default_department_id': self.new_department_id.id,
                'default_career_transition_id': self.id
            },
        }

        return action