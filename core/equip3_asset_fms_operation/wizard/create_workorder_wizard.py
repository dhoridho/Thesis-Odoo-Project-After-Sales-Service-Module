# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _
from datetime import datetime,date
from odoo.exceptions import ValidationError

class WorkOrderWizard(models.TransientModel):
    _name = 'work.order.wizard'
    _description = 'Create Work Order Wizard'

    facility_area = fields.Many2one ('maintenance.facilities.area', string='Facilities Area')
    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset')
    start_date = fields.Date('Start Date',default=datetime.today())
    end_date = fields.Date('End Date', default=datetime.today())
    description = fields.Text('Remarks')
    branch_id = fields.Many2one('res.branch', string='Branch')

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
            vals['branch_id'] = self.branch_id.id
            vals['analytic_group_id'] = [(6, 0, maintenance_request.analytic_group_ids.ids)]
            
            if self.asset_id:
                vals['task_check_list_ids'] = [(0,0, {'equipment_id': maintenance_request.equipment_id.id})]
            mwo_id = self.env['maintenance.work.order'].create(vals)

            if mwo_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Create Work Order'),
                    'res_model': 'maintenance.work.order',
                    'res_id': mwo_id.id,
                    'view_mode': 'form',
                    'target': 'current'
                }
        return True
