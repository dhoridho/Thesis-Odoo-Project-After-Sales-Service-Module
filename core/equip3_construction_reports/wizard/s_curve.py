from odoo import _, api, fields, models
from datetime import datetime


class SCurve(models.TransientModel):
    _name = "s.curve"
    _description = "S-Curve"

    project = fields.Many2one("project.project", string="Project")
    work_orders = fields.Many2many("project.task", string="Job Orders")
    department_type = fields.Selection(related='project.department_type', string='Type of Department')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', 'not in', ('draft','cancelled')), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', 'not in', ('draft','cancelled')), ('company_id', '=', rec.company_id.id,('id','in',self.env.user.project_ids.ids))]}
                }
            else:   
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', 'not in', ('draft','cancelled')), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', 'not in', ('draft','cancelled')), ('company_id', '=', rec.company_id.id)]}
                }
    

    @api.onchange('project')
    def get_workorder(self):
        for res in self:
            workorders = res.env['project.task'].search([('project_id', '=', res.project.id)])
            res.work_orders = [(6, 0, workorders.ids)]

    def create_scurve(self):
        for res in self:
            bud = res.env['project.budget'].search([('project_id', '=', res.project.id)])
            self.env['construction.scurve'].create({
                'name': res.project.name,
                'project_id': res.project.id,
                'start_date': res.project.start_date,
                'end_date': res.project.end_date,
                'job_cost_sheet': res.project.cost_sheet.id,
                'project_budget': bud,
                'contract_amount': res.project.total_estimation_cost,
                'work_orders_ids': [(6, 0, res.work_orders.ids)],
            })
        scurve_id = res.env['construction.scurve'].search([], limit = 1, order = 'id desc')
        return scurve_id.get_formview_action()