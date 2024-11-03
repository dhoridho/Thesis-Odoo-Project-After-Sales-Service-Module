from odoo import models, fields, api


class PropertyProduct(models.Model):
    _inherit = 'product.product'
    
    mwo_count = fields.Integer(compute='_compute_maintenance_count', string='# Maintenance Work Orders')
    mro_count = fields.Integer(compute='_compute_maintenance_count', string='# Maintenance Repair Orders')
    mrq_count = fields.Integer(compute='_compute_maintenance_count', string='# Maintenance Request')
    mpreventive_count = fields.Integer(compute='_compute_maintenance_count', string='# Preventive Maintenance Plans')
    mhourmeter_count = fields.Integer(compute='_compute_maintenance_count', string='Hour Meter Maintenance Plans')
    modometr_count = fields.Integer(compute='_compute_maintenance_count', string='Odometer Maintenance Plans')
    
    def _compute_maintenance_count(self):
        for product in self:
            product.mwo_count = self.env['maintenance.work.order'].search_count([('property_id', '=', product.id)])
            product.mro_count = self.env['maintenance.repair.order'].search_count([('property_id', '=', product.id)])
            product.mrq_count = self.env['maintenance.request'].search_count([('property_id', '=', product.id)])
            product.mpreventive_count = self.env['maintenance.plan'].search_count([('property_id', '=', product.id), ('is_preventive_m_plan', '!=', False)])
            product.mhourmeter_count = self.env['maintenance.plan'].search_count([('property_id', '=', product.id), ('is_hourmeter_m_plan', '!=', False)])
            product.modometr_count = self.env['maintenance.plan'].search_count([('property_id', '=', product.id), ('is_odometer_m_plan', '!=', False)])
    
    def action_mwo_link(self):
        return {
            'name': 'Maintenance Work Orders',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.work.order',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id)],
        }
    
    def action_mro_link(self):
        return {
            'name': 'Maintenance Repair Orders',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.repair.order',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id)],
        }
    
    def action_mrq_link(self):
        return {
            'name': 'Maintenance Request',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id)],
        }
    
    def action_preventive_link(self):
        return {
            'name': 'Preventive Maintenance Plans',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.plan',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('is_preventive_m_plan', '!=', False)],
        }
        
    def action_hourmeter_link(self):
        return {
            'name': 'Hour Meter Maintenance Plans',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.plan',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('is_hourmeter_m_plan', '!=', False)],
        }
    
    def action_odometer_link(self):
        return {
            'name': 'Odometer Maintenance Plans',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.plan',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('is_odometer_m_plan', '!=', False)],
        }
