from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError


class ProjectBudgetInherit(models.Model):
    _inherit = 'project.budget'

    def create_material_request(self):
        if  self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        
        if not self.cost_sheet.warehouse_id:
            raise ValidationError(_("There is no Warehouse selected for this project"))
        
        context = {'default_cost_sheet': self.cost_sheet.id,
                   'default_destination_warehouse': self.cost_sheet.warehouse_id.id,
                   'default_budgeting_period': self.cost_sheet.budgeting_period,
                   'default_analytic_group': [(6, 0, [v.id for v in self.cost_sheet.account_tag_ids])],
                   }
        return {
                'type': 'ir.actions.act_window',
                'name': 'Create Procurement Request',
                'res_model': 'material.request.wiz',
                'view_type': 'form',
                'view_mode': 'form',
                'context': context,
                'target': 'new'
            }