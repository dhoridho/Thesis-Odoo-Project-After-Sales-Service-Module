from pickle import TRUE
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_round

class MaintenanceVehicleOdometer(models.Model):
    _inherit = 'maintenance.vehicle'

    @api.model
    def create(self, vals):
        res = super(MaintenanceVehicleOdometer, self).create(vals)
        res.get_total_value_odoometer()
        res.get_total_value_threshold()
        return res


    #ini jika frequency
    def get_total_value_odoometer(self):
        for record in self:
            maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
            total_odometer = sum(maintenance_id.mapped('value'))
            maintenance_plan = self.env['maintenance.plan'].search(['&','&','&',('start_date', '<=', record.date), 
                                                                                ('end_date', '>=', record.date),
                                                                                ('state','=','active'),
                                                                                ('is_odometer_m_plan','=', True)])
            for plan in maintenance_plan:
                for plan_ids in plan.task_check_list_ids:
                    for line in record.maintenance_vehicle.frequency_odoometer_ids.filtered(lambda line: line.is_odometer_m_plan.id == plan.id):
                        if record.maintenance_vehicle.id == plan_ids.equipment_id.id:
                            if plan.maintenance_frequency_ids > 0:
                                new_floor_value = total_odometer // plan.maintenance_frequency_ids
                                if new_floor_value > line.floorodoo_value:
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
                                            }) for maintenance_list in plan.maintenance_materials_list_ids]
                                    tools_materials_list_ids = [(0, 0, 
                                            {
                                                'product_id': tools_list.product_id.id,
                                                'product_uom_qty': tools_list.product_uom_qty,
                                                'uom_id': tools_list.uom_id.id,
                                                'notes': tools_list.notes,
                                            }) for tools_list in plan.tools_materials_list_ids]

                                    vals = {
                                            'partner_id': plan.partner_id.id,
                                            'facility': record.maintenance_vehicle.fac_area.id,
                                            'maintenanceteam':plan.maintenance_team_id.id ,
                                            'maintenanceassign': plan.m_assignation_type.id,
                                            'ref': plan.name,
                                            'startdate': plan.start_date,
                                            'enddate': plan.end_date,
                                            'branch_id': plan.branch_id.id,
                                            'remarks': plan.remarks,
                                            'user_id': plan.user_id.id,
                                            'company_id': plan.company_id.id,
                                            'task_check_list_ids': task_check_list_ids,
                                            'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                            'tools_materials_list_ids': tools_materials_list_ids,
                                            'maintenance_plan_id': plan.id,
                                            'maintenance_types': [(6, 0, plan.maintenance_types.ids)],
                                            'maintenance_plan_parent_id': plan.id,
                                        }
                                    self.env['maintenance.work.order'].create(vals)


                        

                        


        # for record in self:
        #     maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
        #     total_value = sum(maintenance_id.mapped('value'))
        #     if record.maintenance_vehicle.frequency_odoometer_ids:
        #         for line in record.maintenance_vehicle.frequency_odoometer_ids:
        #             print('line.floorodoo_valueline.floorodoo_valueline.floorodoo_value',line.floorodoo_value)
        #             maintenance_frequency = line.is_odometer_m_plan.maintenance_frequency_ids
        #             if maintenance_frequency > 0:
        #                 new_floor_value = total_value // maintenance_frequency
        #                 plan_id = line.is_odometer_m_plan
        #                 if record.date >= plan_id.start_date \
        #                 and record.date <= plan_id.end_date \
        #                 and new_floor_value > line.floorodoo_value:
        #                     line.floorodoo_value = new_floor_value
        #                     task_check_list_ids = [(0, 0, {
        #                             'equipment_id': record.maintenance_vehicle.id,
        #                         })]
        #                     maintenance_materials_list_ids = [(0, 0, 
        #                         {
        #                             'product_id': maintenance_list.product_id.id,
        #                             'product_uom_qty': maintenance_list.product_uom_qty,
        #                             'uom_id': maintenance_list.uom_id.id,
        #                             'notes': maintenance_list.notes,
        #                             'price_unit': maintenance_list.product_id.standard_price,
        #                             'price_subtotal': maintenance_list.price_subtotal,
        #                         }) for maintenance_list in plan_id.maintenance_materials_list_ids]
        #                     tools_materials_list_ids = [(0, 0, 
        #                         {
        #                             'product_id': tools_list.product_id.id,
        #                             'product_uom_qty': tools_list.product_uom_qty,
        #                             'uom_id': tools_list.uom_id.id,
        #                             'notes': tools_list.notes,
        #                         }) for tools_list in plan_id.tools_materials_list_ids]
        #                     vals = {
        #                         'partner_id': plan_id.partner_id.id,
        #                         'facility': record.maintenance_vehicle.fac_area.id,
        #                         'maintenanceteam':plan_id.maintenance_team_id.id ,
        #                         'maintenanceassign': plan_id.m_assignation_type.id,
        #                         'ref': plan_id.name,
        #                         'startdate': plan_id.start_date,
        #                         'enddate': plan_id.end_date,
        #                         'branch_id': plan_id.branch_id.id,
        #                         'remarks': plan_id.remarks,
        #                         'user_id': plan_id.user_id.id,
        #                         'company_id': plan_id.company_id.id,
        #                         'task_check_list_ids': task_check_list_ids,
        #                         'maintenance_materials_list_ids': maintenance_materials_list_ids,
        #                         'tools_materials_list_ids': tools_materials_list_ids,
        #                         'maintenance_plan_id': plan_id.id,
        #                         'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
        #                     }
        #                     self.env['maintenance.work.order'].create(vals)



    # ini jika threshold
    def get_total_value_threshold(self):
        for record in self:
            maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
            total_value = sum(maintenance_id.mapped('value'))
            maintenance_plan = self.env['maintenance.plan'].search(['&','&','&',('start_date', '<=', record.date), 
                                                                                ('end_date', '>=', record.date),
                                                                                ('state','=','active'),
                                                                                ('is_odometer_m_plan','=', True)])
            for plan in maintenance_plan:
                if record.value > 0:
                    for plan_ids in plan.task_check_list_ids:
                        if record.maintenance_vehicle.id == plan_ids.equipment_id.id:
                            if plan.maintenance_threshold_ids:
                                for line in record.maintenance_vehicle.threshold_odoometer_ids.filtered(lambda line: line.is_odometer.id == plan.id):
                                    threshold_ids = line.is_odometer.maintenance_threshold_ids
                                    current_value = sorted(threshold_ids.mapped('threshold'), reverse=True)
                                    for th in current_value:
                                        if total_value >= th and th > line.last_threshold:
                                            line.last_threshold = th
                                            task_check_list_ids = [(0, 0, {
                                                'equipment_id': record.maintenance_vehicle.id,
                                                'vehicle_parts_ids': [(6, 0, plan_ids.vehicle_parts_ids.ids)],
                                                'task': plan_ids.task,
                                            })]
                                            maintenance_materials_list_ids = [(0, 0, 
                                                {
                                                    'product_id': maintenance_list.product_id.id,
                                                    'price_unit': maintenance_list.product_id.standard_price,
                                                    'product_uom_qty': maintenance_list.product_uom_qty,
                                                    'uom_id': maintenance_list.uom_id.id,
                                                    'notes': maintenance_list.notes,
                                                    'price_subtotal': maintenance_list.price_subtotal,
                                                }) for maintenance_list in plan.maintenance_materials_list_ids]

                                            tools_materials_list_ids = [(0, 0, 
                                                {
                                                    'product_id': tools_list.product_id.id,
                                                    'product_uom_qty': tools_list.product_uom_qty,
                                                    'uom_id': tools_list.uom_id.id,
                                                    'notes': tools_list.notes,
                                                }) for tools_list in plan.tools_materials_list_ids]
                                            vals = {
                                                'partner_id': plan.partner_id.id,
                                                'facility': record.maintenance_vehicle.fac_area.id,
                                                'maintenanceteam':plan.maintenance_team_id.id ,
                                                'maintenanceassign': plan.m_assignation_type.id,
                                                'ref': plan.name,
                                                'startdate': plan.start_date,
                                                'enddate': plan.end_date,
                                                'branch_id': plan.branch_id.id,
                                                'remarks': plan.remarks,
                                                'user_id': plan.user_id.id,
                                                'company_id': plan.company_id.id,
                                                'task_check_list_ids': task_check_list_ids,
                                                #'maintenance_materials_list_ids': maintenance_materials_list_ids,
                                                'tools_materials_list_ids': tools_materials_list_ids,
                                                'maintenance_plan_id': plan.id,
                                                'maintenance_types': [(6, 0, plan.maintenance_types.ids)],
                                                'maintenance_plan_parent_id': plan.id,
                                                }
                                            self.env['maintenance.work.order'].create(vals)
                else:
                    for plan in maintenance_plan:
                        if plan.maintenance_threshold_ids:
                            for line in record.maintenance_vehicle.threshold_odoometer_ids.filtered(lambda line: line.is_odometer.id == plan.id):
                                threshold_ids = line.is_odometer.maintenance_threshold_ids
                                current_value = sorted(threshold_ids.mapped('threshold'), reverse=True)
                                for x in current_value:
                                    if record.total_value < line.last_threshold:
                                            line.last_threshold = x

                                

        # for record in self:
        #     maintenance_id = self.search([('maintenance_vehicle', '=', record.maintenance_vehicle.id)])
        #     total_value = sum(maintenance_id.mapped('value'))
        #     print('total_valuetotal_value',total_value)
        #     if record.maintenance_vehicle.threshold_odoometer_ids:
        #         for line in record.maintenance_vehicle.threshold_odoometer_ids:
        #             threshold_ids = line.is_odometer.maintenance_threshold_ids
        #             plan_id = line.is_odometer
        #             current_value = sorted(threshold_ids.mapped('threshold'), reverse=True)
        #             for th in current_value:
        #                 if total_value >= th and record.date >= plan_id.start_date \
        #                     and record.date <= plan_id.end_date \
        #                     and th > line.last_threshold:
        #                     line.last_threshold = th
        #                     task_check_list_ids = [(0, 0, {
        #                             'equipment_id': record.maintenance_vehicle.id,
        #                         })]
        #                     maintenance_materials_list_ids = [(0, 0, 
        #                         {
        #                             'product_id': maintenance_list.product_id.id,
        #                             'price_unit': maintenance_list.product_id.standard_price,
        #                             'product_uom_qty': maintenance_list.product_uom_qty,
        #                             'uom_id': maintenance_list.uom_id.id,
        #                             'notes': maintenance_list.notes,
        #                             'price_subtotal': maintenance_list.price_subtotal,
        #                         }) for maintenance_list in plan_id.maintenance_materials_list_ids]
        #                     tools_materials_list_ids = [(0, 0, 
        #                         {
        #                             'product_id': tools_list.product_id.id,
        #                             'product_uom_qty': tools_list.product_uom_qty,
        #                             'uom_id': tools_list.uom_id.id,
        #                             'notes': tools_list.notes,
        #                         }) for tools_list in plan_id.tools_materials_list_ids]
        #                     vals = {
        #                         'partner_id': plan_id.partner_id.id,
        #                         'facility': record.maintenance_vehicle.fac_area.id,
        #                         'maintenanceteam':plan_id.maintenance_team_id.id ,
        #                         'maintenanceassign': plan_id.m_assignation_type.id,
        #                         'ref': plan_id.name,
        #                         'startdate': plan_id.start_date,
        #                         'enddate': plan_id.end_date,
        #                         'branch': plan_id.branch_id.id,
        #                         'branch_id': plan_id.branch_id.id,
        #                         'remarks': plan_id.remarks,
        #                         'user_id': plan_id.user_id.id,
        #                         'company_id': plan_id.company_id.id,
        #                         'task_check_list_ids': task_check_list_ids,
        #                         'maintenance_materials_list_ids': maintenance_materials_list_ids,
        #                         'tools_materials_list_ids': tools_materials_list_ids,
        #                         'maintenance_plan_id': plan_id.id,
        #                         'maintenance_types': [(6, 0, plan_id.maintenance_types.ids)],
        #                     }
        #                     self.env['maintenance.work.order'].create(vals)

