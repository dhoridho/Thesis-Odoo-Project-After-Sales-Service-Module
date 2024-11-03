from odoo import models, fields, api, _

class RepairHistoryLine(models.Model):
    _name = 'repair.history.line'
    _description = 'Repair History Line'
    _rec_name = 'maintenance_ro_id'

    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    maintenance_ro_id = fields.Many2one(comodel_name='maintenance.repair.order', string='Maintenance Repair Order')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
class MaintenanceEquipmentHistoryLine(models.Model):
    _inherit = 'maintenance.equipment'

    repair_history_line_ids = fields.One2many(comodel_name='repair.history.line', inverse_name='equipment_id', string='Repair History Line')
    history_repair_count = fields.Integer(string='Repair Count', compute='_compute_history_repair_count', store=True)
    

    @api.depends('repair_history_line_ids')
    def _compute_history_repair_count(self):
        for rec in self:
            rec.history_repair_count = 0
            if rec.repair_history_line_ids:
                rec.history_repair_count = len(rec.repair_history_line_ids)

    def repair_history_cron(self):
        for rec in self.env['maintenance.equipment'].search([]):
            plan_tasks = self.env['plan.task.check.list'].search([('equipment_id', '=', rec.id), ('maintenance_ro_id', '!=', False), ('is_created_history', '=', False)])
            for task in plan_tasks:
                if task.maintenance_ro_id.state_id == 'done':
                    vals = {
                        'equipment_id': rec.id,
                        'maintenance_ro_id': task.maintenance_ro_id.id,
                        'start_date': task.maintenance_ro_id.date_start,
                        'end_date': task.maintenance_ro_id.date_stop,
                    }
                    rec.repair_history_line_ids.create(vals)
                    task.is_created_history = True

class PlanTaskCheckListInherit(models.Model):
    _inherit = 'plan.task.check.list'

    is_created_history = fields.Boolean(string='Is Created History', default=False)