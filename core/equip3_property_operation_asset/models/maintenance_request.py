from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'
    
    property_id = fields.Many2one(comodel_name='product.product', string='Property', domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    
    def create_work_order_wizard(self):
        view_id = self.env.ref('equip3_asset_fms_operation.create_work_order_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': ('Create Work Order'),
            'res_model': 'work.order.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {
                'default_asset_id': self.equipment_id.id,
                'default_facility_area':self.facility_area.id,
                'default_property_id':self.property_id.id,
                'default_description':self.remarks,
                'request_note':self.note,
                'default_ref':self.name,
            }
        }

class MaintenanceWorkOrder(models.Model):
    _inherit = 'maintenance.work.order'

    property_id = fields.Many2one(comodel_name='product.product', string='Property', domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    
    def action_create_repair_order(self):
        repair_order_id = self.env['maintenance.repair.order'].create({
            'created_date': self.created_date,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch.id,
            'date_start': self.startdate,
            'date_stop': self.enddate,
            'facilities_area': self.facility.id,
            'maintenance_team': self.maintenanceteam.id,
            'maintenance_assignation_type': self.maintenanceassign.id,
            'ref': self.name,
            'remarks': self.remarks,
            'analytic_group_id': self.analytic_group_id.id,
            'work_order_id': self.id,
            'maintenance_types': [(6, 0, self.maintenance_types.ids)],
            'property_id': self.property_id.id,
        })
        if repair_order_id:
            for tas in self.task_check_list_ids:
                repair_order_id.task_check_list_ids = [(0, 0, {
                    'equipment_id': tas.equipment_id.id,
                    'task': tas.task,
                })]
            for tools in self.tools_materials_list_ids:
                repair_order_id.tools_materials_list_ids = [(0, 0, {
                    'product_id': tools.product_id.id,
                    'uom_id': tools.uom_id.id,
                })]
            for material in self.maintenance_materials_list_ids:
                repair_order_id.maintenance_materials_list_ids = [(0, 0, {
                    'product_id': material.product_id.id,
                    'uom_id': material.uom_id.id,
                })]

class MaintenanceRepairOrder(models.Model):
    _inherit = 'maintenance.repair.order'

    property_id = fields.Many2one(comodel_name='product.product', string='Property', domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    
