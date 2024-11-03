from odoo import _, api, fields, models



class PlanTaskCheckList(models.Model):
    _inherit = 'plan.task.check.list'

    remaining_budget = fields.Float(string='Remaining Budget', compute="compute_remaining_budget")
    used_budget = fields.Float(string='Used Budget', compute="compute_budget")
    
    @api.depends('equipment_id', 
                 'maintenance_wo_id.branch_id', 'maintenance_wo_id.analytic_group_id', 'maintenance_wo_id.startdate', 'maintenance_wo_id.enddate', 
                 'maintenance_ro_id.branch_id', 'maintenance_ro_id.analytic_group_id', 'maintenance_ro_id.date_start', 'maintenance_ro_id.date_stop')
    def compute_remaining_budget(self):
        """ sum total remaining budget from asset budget accounting"""
        for task in self:

            task.remaining_budget = 0.0
            asset_budget = task._get_asset_budget(task.equipment_id)
            if asset_budget:
                task.remaining_budget = asset_budget or 0.0
                
    
    @api.depends('maintenance_wo_id.maintenance_materials_list_ids', 'maintenance_ro_id.maintenance_materials_list_ids')
    def compute_budget(self):
        """Sum total used budget from maintenance materials list"""
        
        for task in self:
            task.used_budget = 0.0

            materials = []
            if task.maintenance_ro_id:
                materials.extend(task.maintenance_ro_id.maintenance_materials_list_ids)
            if task.maintenance_wo_id:
                materials.extend(task.maintenance_wo_id.maintenance_materials_list_ids)
            
            task.used_budget = sum(
                material.price_unit * material.product_uom_qty
                for material in materials
                if task.equipment_id.id == material.parent_equipment_id.id
            )