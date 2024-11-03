from odoo import _, api, fields, models


class JobEstimateToVariation(models.TransientModel):
    _name = 'job.estimate.variation.const'
    _description = 'Change to Variation Order'

    txt = fields.Text(string="Information",default="Sale Order main contract for this project has been confirmed. Do you want to change category of this BOQ to variation order?")

    def _prepare_value(self, main_contract):
        return{'name': self.env['ir.sequence'].next_by_code('job.sequence.vo'),
                      'state':'draft',
                      'state_new':'draft',
                      'contract_category' :'var',
                      'main_contract_ref': main_contract,
                      'project_scope_ids': False,
                      'section_ids': False,
                      'variable_ids': False,
                      'material_estimation_ids': False,
                      'labour_estimation_ids': False,
                      'overhead_estimation_ids': False,
                      'equipment_estimation_ids': False,
                      'internal_asset_ids': False,
                      'subcon_estimation_ids': False,
                    }
            
    def action_confirm(self):
        job_id = self.env['job.estimate'].browse([self._context.get('active_id')])
        main_contract = self.env['sale.order.const'].search([('project_id', '=', job_id.project_id.id), ('contract_category', '=', 'main'), ('state', 'in', ['sale','done'])], limit=1)    
        job_id.write(self._prepare_value(main_contract))