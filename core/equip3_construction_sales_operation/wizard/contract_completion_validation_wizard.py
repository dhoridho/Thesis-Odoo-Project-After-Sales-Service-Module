from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class ContractCompletionValidationWizard(models.TransientModel):
    _name = 'contract.completion.validation.wizard'
    _description = 'Contract Caompletion Confirmation Wizard'

    txt = fields.Text(string="Confirmation",default="The total of stage weightage is less than 100%.\nDo you want to continue?")
    contract_completion_id = fields.Many2one('project.completion.const', string='contract_completion_id')

    def action_confirm(self):
        # Let the wizard close and return to the form view
        pass

    def action_cancel(self):
        # redirect to contract completion form view
        return {
            'name': ("Contract Completion"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'res_id': self.contract_completion_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        

    