from odoo import api, models, fields

class AssetFlowWizard(models.TransientModel):
    _name = 'asset.flow.wizard'

    name = fields.Char(string='Name', default='Asset Flow')

    def button_asset(self):
        action = self.env.ref('equip3_asset_fms_masterdata.modul_asset_action').read()[0]
        return action

    def button_vehicle(self):
        action = self.env.ref('equip3_asset_fms_masterdata.maintenance_vehicle_action').read()[0]
        return action

    def button_asset_control(self):
        action = self.env.ref('equip3_asset_fms_dashboard.ks_asset').read()[0]
        return action

    def button_mt_request(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'name': ('Maintenance Request'),
            'res_model': 'maintenance.request',
            'view_id': False,
        }
        return action

    def button_mt_work_order(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'name': ('Maintenance Work Order'),
            'res_model': 'maintenance.work.order',
            'view_id': False,
        }
        return action

    def button_mt_repair_order(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'name': ('Maintenance Repair Order'),
            'res_model': 'maintenance.repair.order',
            'view_id': False,
        }
        return action

    def button_preventive_mt_plan(self):
        action = self.env.ref('equip3_asset_fms_operation.maintenance_plan_action_preventive').read()[0]
        return action

    def button_hour_meter_mt_plan(self):
        action = self.env.ref('equip3_asset_fms_operation.maintenance_plan_action_hourmeter').read()[0]
        return action

    def button_odoometer_mt_plan(self):
        action = self.env.ref('equip3_asset_fms_operation.maintenance_plan_action_odometer').read()[0]
        return action

    def button_asset_cost_report(self):
        action = self.env.ref('equip3_asset_fms_report.asset_cost_report_pivot_action').read()[0]
        return action

    def button_vehicle_cost_report(self):
        action = self.env.ref('equip3_asset_fms_report.vehicle_cost_report_action').read()[0]
        return action

    def button_mt_request_report(self):
        action = self.env.ref('equip3_asset_fms_report.action_report_maintenance_request').read()[0]
        return action

    def button_fee_head(self):
        action = self.env.ref('sale.action_orders').read()[0]
        return action