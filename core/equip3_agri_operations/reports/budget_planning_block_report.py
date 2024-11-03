from odoo import models, fields, api


class ReportBudgetPlanningBlockReport(models.AbstractModel):
    _name = 'report.equip3_agri_operations.budget_planning_block_report'
    _description = 'Report Budget Planning Block Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['agriculture.budget.planning.block'].browse(docids),
            'doc_model': 'agriculture.budget.planning.block',
        }
