from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CreateWorkOrderWizard(models.TransientModel):
    _inherit = 'work.order.wizard'
    
    property_id = fields.Many2one(comodel_name='product.product', string='Property', domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    
    def create_work_order(self):
        active_id = self.env.context.get('active_id')
        maintenance_request = self.env['maintenance.request'].search([('id', '=', active_id)])
        if self.start_date > self.end_date:
            raise ValidationError("End date must be greater than start date!")
        else:
            vals = {}
            vals['facility'] =self.facility_area.id if self.facility_area else False
            vals['equipment_id'] =self.asset_id.id if self.asset_id else False
            vals['remarks'] =self.description if self.description else False
            vals['maintainence_request_id'] = self.env.context.get('active_id')
            vals['instructions'] = self.env.context.get('request_note')
            vals['startdate'] = self.start_date
            vals['enddate'] = self.end_date
            vals['ref'] = maintenance_request.name
            vals['property_id'] = self.property_id.id if self.property_id else False

            if self.asset_id:
                vals['task_check_list_ids'] = [(0,0, {'equipment_id': maintenance_request.equipment_id.id})]
            self.env['maintenance.work.order'].create(vals)
        return True
    
    
