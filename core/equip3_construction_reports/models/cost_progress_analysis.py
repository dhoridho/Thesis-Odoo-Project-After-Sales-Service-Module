from odoo import api, fields, models


class CostProgressAnalysis(models.Model):
    _inherit = 'project.project'
    _description = 'Project'

    cost_to_complete = fields.Float(string='Cost to Complete', readonly=True, compute ='_comute_cost_complete', store=True)
    project_total_claim_from_invoice = fields.Monetary(string='Total Claim from Invoice', compute='_compute_total_claim_from_invoice',store=True)

    def custom_menu_cost_progress_management(self):
        if self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Progress Analysis',
                'res_model': 'project.project',
                'view_mode': 'pivot,tree',
                # 'views':views,
                'domain': [('department_type', '=', 'project'),('name','in',[data.name for data in self.env.user.project_ids])],
                'context':{'default_department_type': 'project'}
            }
        else:
           return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Progress Analysis',
                'res_model': 'project.project',
                'view_mode':'pivot,tree',
                # 'views':views,
                'domain': [('department_type', '=', 'project')],
                'context':{'default_department_type': 'project'}
            }
           
    def custom_menu_cost_progress(self):
        if self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Progress Analysis',
                'res_model': 'project.project',
                'view_mode': 'pivot,tree',
                # 'views':views,
                'domain': [('department_type', '=', 'department'),('name','in',[data.name for data in self.env.user.project_ids])],
                'context':{'default_department_type': 'department'}
            }
        else:
           return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Progress Analysis',
                'res_model': 'project.project',
                'view_mode':'pivot,tree',
                # 'views':views,
                'domain': [('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'}
            }

    def _compute_cost(self):
        res = super(CostProgressAnalysis, self)._compute_cost()
        for rec in self:
            rec._comute_cost_complete()
            rec._compute_total_claim_from_invoice()
        return res
    
    def _comute_cost_complete(self):
        for res in self:
            cost = res.total_estimation_cost - res.total_actual_cost
            res.cost_to_complete = cost

    def _compute_total_claim_from_invoice(self):
        for line in self:
            record = self.env['progressive.claim'].search(
                [('progressive_bill', '=', False), ('project_id', '=', line.id)])
            for rec in record:
                inv = (100 - rec.down_payment - rec.retention1 - rec.retention2)
                line.project_total_claim_from_invoice = inv * rec.contract_amount * rec.invoiced_progress