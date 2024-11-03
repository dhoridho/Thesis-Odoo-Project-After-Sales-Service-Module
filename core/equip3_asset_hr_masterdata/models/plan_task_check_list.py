from odoo import models, fields, api, _
import json

class PlanTaskCheckListInherit(models.Model):
    _inherit = 'plan.task.check.list'

    equipment_id_domain = fields.Char(string='Equipment Domain', compute='_compute_equipment_id_domain')

    @api.depends('maintenance_wo_id.department_ids','maintenance_ro_id.department_ids')
    def _compute_equipment_id_domain(self):
        for rec in self:
            if rec.maintenance_wo_id:
                equipment_ids = self.env['maintenance.equipment'].search([('department_id', '=', rec.maintenance_wo_id.department_ids.ids)])
                rec.equipment_id_domain = json.dumps([('id', 'in', equipment_ids.ids)])
            elif rec.maintenance_ro_id:
                equipment_ids = self.env['maintenance.equipment'].search([('department_id', '=', rec.maintenance_ro_id.department_ids.ids)])
                rec.equipment_id_domain = json.dumps([('id', 'in', equipment_ids.ids)])