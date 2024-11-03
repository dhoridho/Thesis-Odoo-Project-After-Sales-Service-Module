from odoo import models, fields, api, _
from datetime import datetime, date, timedelta


class MaintenancePlan(models.Model):
    _inherit = 'maintenance.plan'
    
    property_id = fields.Many2one('product.product', string='Property', domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    
    def create_workorder(self):
        asset_lst = []
        plan_data = self.env['maintenance.plan'].search([('is_preventive_m_plan', '=', True), ('start_date', '!=', False), ('end_date', '!=', False), ('frequency_interval_number', '!=', False)])
        for plan in plan_data:
            work_order = self.env['maintenance.work.order'].search([('maintenance_plan_id', '=', plan.id), ('startdate', '=', self.get_today())])
            if not work_order and plan.state == 'active':
                if plan.start_date <= self.get_today() and plan.end_date >= self.get_today():
                    if plan.start_date == self.get_today() or plan.next_wo_date == self.get_today():
                        work_order_id = self.env['maintenance.work.order'].create({
                            'partner_id': plan.partner_id.id,
                            'facility': plan.facility_area.id,
                            'user_id': plan.user_id.id,
                            'maintenanceteam': plan.maintenance_team_id.id,
                            'maintenanceassign': plan.m_assignation_type.id,
                            'branch': plan.branch_id.id,
                            'company_id': plan.company_id.id,
                            'remarks': plan.remarks,
                            'maintenance_plan_id': plan.id,
                            'ref': plan.name,
                            'startdate': self.get_today(),
                            'enddate': self.get_today(),
                            'maintenance_types': [(6, 0, plan.maintenance_types.ids)],
                            'property_id': plan.property_id.id,
                        })
                        for material in plan.maintenance_materials_list_ids:
                            work_order_id.maintenance_materials_list_ids = [(0, 0, {
                                'product_id': material.product_id.id,
                                'product_uom_qty': material.product_uom_qty,
                                'uom_id': material.uom_id.id,
                                'notes': material.notes,
                            })]
                        for tool in plan.tools_materials_list_ids:
                            work_order_id.tools_materials_list_ids = [(0, 0, {
                                'product_id': tool.product_id.id,
                                'product_uom_qty': tool.product_uom_qty,
                                'uom_id': tool.uom_id.id,
                                'notes': tool.notes,
                            })]
                        for task_check in plan.task_check_list_ids:
                            work_order_id.task_check_list_ids = [(0, 0, {
                                'equipment_id': task_check.equipment_id.id,
                                'task': task_check.task,
                            })]
                        for asset in plan.maintenance_category_ids:
                            asset_lst = asset.equipment_ids.ids
                            for eq_id in asset_lst:
                                work_order_id.task_check_list_ids = [(0, 0, {
                                    'equipment_id': eq_id,
                                })]
                        if work_order_id:
                            plan.next_wo_date = self.get_today() + timedelta(days=plan.frequency_interval_number)
                            if plan.next_wo_date > plan.end_date:
                                plan.state = 'done'

class MaintenanceHourMeter(models.Model):
    _inherit = 'maintenance.hour.meter'
    
    def get_total_value_hourmeter(self):
        for record in self:
            maintenance_ho_id = self.search([('maintenance_asset', '=', record.maintenance_asset.id)])
            total_value = sum(maintenance_ho_id.mapped('value'))
            if record.maintenance_asset.frequency_hourmeter_ids:
                for line in record.maintenance_asset.frequency_hourmeter_ids:
                    maintenance_frequency = line.is_hourmeter_m_plan.maintenance_frequency_ids
                    if maintenance_frequency > 0:
                        new_floor_value = total_value // maintenance_frequency
                        plan_id = line.is_hourmeter_m_plan
                        if record.date >= plan_id.start_date \
                        and record.date <= plan_id.end_date \
                        and new_floor_value > line.floorhour_value:
                            line.floorhour_value = new_floor_value
                            task_check_list_ids = [(0, 0, {
                                    'equipment_id': record.maintenance_asset.id,
                                })]
                            maintenance_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': maintenance_list.product_id.id,
                                    'price_unit': maintenance_list.product_id.standard_price,
                                    'product_uom_qty': maintenance_list.product_uom_qty,
                                    'uom_id': maintenance_list.uom_id.id,
                                    'notes': maintenance_list.notes,
                                    'price_subtotal': maintenance_list.price_subtotal,
                                }) for maintenance_list in plan_id.maintenance_materials_list_ids]
                            tools_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': tools_list.product_id.id,
                                    'product_uom_qty': tools_list.product_uom_qty,
                                    'uom_id': tools_list.uom_id.id,
                                    'notes': tools_list.notes,
                                }) for tools_list in plan_id.tools_materials_list_ids]
                            vals = {
                                'partner_id': plan_id.partner_id.id,
                                'facility': record.maintenance_asset.fac_area.id,
                                'maintenanceteam':plan_id.maintenance_team_id.id ,
                                'maintenanceassign': plan_id.m_assignation_type.id,
                                'ref': plan_id.name,
                                'startdate': plan_id.start_date,
                                'enddate': plan_id.end_date,
                                'branch': plan_id.branch_id.id,
                                'remarks': plan_id.remarks,
                                'user_id': plan_id.user_id.id,
                                'company_id': plan_id.company_id.id,
                                'task_check_list_ids': task_check_list_ids,
                                'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                'tools_materials_list_ids': tools_materials_list_ids,
                                'maintenance_plan_id': plan_id.id,
                                'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
                                'property_id': plan_id.property_id.id,
                            }
                            self.env['maintenance.work.order'].create(vals)


    def get_total_value_threshold(self):
        for record in self:
            maintenance_ho_id = self.search([('maintenance_asset', '=', record.maintenance_asset.id)])
            total_value = sum(maintenance_ho_id.mapped('value'))
            if record.maintenance_asset.threshold_hourmeter_ids:
                for line in record.maintenance_asset.threshold_hourmeter_ids:
                    threshold_ids = line.is_hourmeter.maintenance_threshold_ids
                    plan_id = line.is_hourmeter
                    current_value = sorted(threshold_ids.mapped('threshold'), reverse=True)
                    for th in current_value:
                        if total_value >= th and record.date >= plan_id.start_date \
                            and record.date <= plan_id.end_date \
                            and th > line.last_threshold:
                            line.last_threshold = th
                            task_check_list_ids = [(0, 0, {
                                    'equipment_id': record.maintenance_asset.id,
                                })]
                            maintenance_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': maintenance_list.product_id.id,
                                    'price_unit': maintenance_list.product_id.standard_price,
                                    'product_uom_qty': maintenance_list.product_uom_qty,
                                    'uom_id': maintenance_list.uom_id.id,
                                    'notes': maintenance_list.notes,
                                    'price_subtotal': maintenance_list.price_subtotal,
                                }) for maintenance_list in plan_id.maintenance_materials_list_ids]
                            tools_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': tools_list.product_id.id,
                                    'product_uom_qty': tools_list.product_uom_qty,
                                    'uom_id': tools_list.uom_id.id,
                                    'notes': tools_list.notes,
                                }) for tools_list in plan_id.tools_materials_list_ids]
                            vals = {
                                'partner_id': plan_id.partner_id.id,
                                'facility': record.maintenance_asset.fac_area.id,
                                'maintenanceteam':plan_id.maintenance_team_id.id ,
                                'maintenanceassign': plan_id.m_assignation_type.id,
                                'ref': plan_id.name,
                                'startdate': plan_id.start_date,
                                'enddate': plan_id.end_date,
                                'branch': plan_id.branch_id.id,
                                'remarks': plan_id.remarks,
                                'user_id': plan_id.user_id.id,
                                'company_id': plan_id.company_id.id,
                                'task_check_list_ids': task_check_list_ids,
                                'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                'tools_materials_list_ids': tools_materials_list_ids,
                                'maintenance_plan_id': plan_id.id,
                                'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
                                'property_id': plan_id.property_id.id,
                            }
                            self.env['maintenance.work.order'].create(vals)
                            
class MaintenanceOdoometer(models.Model):
    _inherit = 'maintenance.vehicle'
    
    def get_total_value_odoometer(self):
        for record in self:
            maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
            total_value = sum(maintenance_id.mapped('value'))
            if record.maintenance_vehicle.frequency_odoometer_ids:
                for line in record.maintenance_vehicle.frequency_odoometer_ids:
                    maintenance_frequency = line.is_odometer_m_plan.maintenance_frequency_ids
                    if maintenance_frequency > 0:
                        new_floor_value = total_value // maintenance_frequency
                        plan_id = line.is_odometer_m_plan
                        if record.date >= plan_id.start_date \
                        and record.date <= plan_id.end_date \
                        and new_floor_value > line.floorodoo_value:
                            line.floorodoo_value = new_floor_value
                            task_check_list_ids = [(0, 0, {
                                    'equipment_id': record.maintenance_vehicle.id,
                                })]
                            maintenance_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': maintenance_list.product_id.id,
                                    'product_uom_qty': maintenance_list.product_uom_qty,
                                    'uom_id': maintenance_list.uom_id.id,
                                    'notes': maintenance_list.notes,
                                    'price_unit': maintenance_list.product_id.standard_price,
                                    'price_subtotal': maintenance_list.price_subtotal,
                                }) for maintenance_list in plan_id.maintenance_materials_list_ids]
                            tools_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': tools_list.product_id.id,
                                    'product_uom_qty': tools_list.product_uom_qty,
                                    'uom_id': tools_list.uom_id.id,
                                    'notes': tools_list.notes,
                                }) for tools_list in plan_id.tools_materials_list_ids]
                            vals = {
                                'partner_id': plan_id.partner_id.id,
                                'facility': record.maintenance_vehicle.fac_area.id,
                                'maintenanceteam':plan_id.maintenance_team_id.id ,
                                'maintenanceassign': plan_id.m_assignation_type.id,
                                'ref': plan_id.name,
                                'startdate': plan_id.start_date,
                                'enddate': plan_id.end_date,
                                'branch': plan_id.branch_id.id,
                                'remarks': plan_id.remarks,
                                'user_id': plan_id.user_id.id,
                                'company_id': plan_id.company_id.id,
                                'task_check_list_ids': task_check_list_ids,
                                'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                'tools_materials_list_ids': tools_materials_list_ids,
                                'maintenance_plan_id': plan_id.id,
                                'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
                                'property_id': plan_id.property_id.id,
                            }
                            self.env['maintenance.work.order'].create(vals)


    def get_total_value_threshold(self):
        for record in self:
            maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
            total_value = sum(maintenance_id.mapped('value'))
            if record.maintenance_vehicle.threshold_odoometer_ids:
                for line in record.maintenance_vehicle.threshold_odoometer_ids:
                    threshold_ids = line.is_odometer.maintenance_threshold_ids
                    plan_id = line.is_odometer
                    current_value = sorted(threshold_ids.mapped('threshold'), reverse=True)
                    for th in current_value:
                        if total_value >= th and record.date >= plan_id.start_date \
                            and record.date <= plan_id.end_date \
                            and th > line.last_threshold:
                            line.last_threshold = th
                            task_check_list_ids = [(0, 0, {
                                    'equipment_id': record.maintenance_vehicle.id,
                                })]
                            maintenance_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': maintenance_list.product_id.id,
                                    'price_unit': maintenance_list.product_id.standard_price,
                                    'product_uom_qty': maintenance_list.product_uom_qty,
                                    'uom_id': maintenance_list.uom_id.id,
                                    'notes': maintenance_list.notes,
                                    'price_subtotal': maintenance_list.price_subtotal,
                                }) for maintenance_list in plan_id.maintenance_materials_list_ids]
                            tools_materials_list_ids = [(0, 0, 
                                {
                                    'product_id': tools_list.product_id.id,
                                    'product_uom_qty': tools_list.product_uom_qty,
                                    'uom_id': tools_list.uom_id.id,
                                    'notes': tools_list.notes,
                                }) for tools_list in plan_id.tools_materials_list_ids]
                            vals = {
                                'partner_id': plan_id.partner_id.id,
                                'facility': record.maintenance_vehicle.fac_area.id,
                                'maintenanceteam':plan_id.maintenance_team_id.id ,
                                'maintenanceassign': plan_id.m_assignation_type.id,
                                'ref': plan_id.name,
                                'startdate': plan_id.start_date,
                                'enddate': plan_id.end_date,
                                'branch': plan_id.branch_id.id,
                                'remarks': plan_id.remarks,
                                'user_id': plan_id.user_id.id,
                                'company_id': plan_id.company_id.id,
                                'task_check_list_ids': task_check_list_ids,
                                'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                'tools_materials_list_ids': tools_materials_list_ids,
                                'maintenance_plan_id': plan_id.id,
                                'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
                                'property_id': plan_id.property_id.id,
                            }
                            self.env['maintenance.work.order'].create(vals)

