from odoo import api, fields, models, _


class ProjectTaskNew(models.Model):
    _inherit = 'project.task'

    production_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    is_engineering = fields.Boolean(string="Is Engineering", default=False)
    total_production_record = fields.Integer(compute='_compute_count_record_cons')

    def _compute_count_record_cons(self):
        for order in self:
            record_count = self.env['mrp.consumption'].search_count([('project_id', '=', self.project_id.id), ('cost_sheet', '=', self.cost_sheet.id), ('job_order', '=', self.id)])
            order.total_production_record = record_count

    @api.onchange('project_id')
    def onchange_project_enginerring(self):
        if self.project_id:
            # self.is_engineering = False
            if self.project_id.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False
        else:
            self.is_engineering = False

    def action_mrp_order_cons(self):
        action = self.production_id.get_formview_action()
        action['domain'] = [('id', '=', self.production_id.id)]
        return action
    
    def action_production_record(self):
        return {
            'name': ("Production Record"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.consumption',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id), ('cost_sheet', '=', self.cost_sheet.id), ('job_order', '=', self.id)],
        }
    
class ProgressHistoryInherit(models.Model):
    _inherit = 'progress.history'

    production_id = fields.Many2one(related='work_order.production_id', string="Production Order")
    workorder_id = fields.Many2one('mrp.workorder', string="Production Work Order")
    record_id = fields.Many2one('mrp.consumption', string="Production Record")
    
    def action_production_record_cons(self):
        action = self.record_id.get_formview_action()
        action['domain'] = [('id', '=', self.record_id.id)]
        return action
    
