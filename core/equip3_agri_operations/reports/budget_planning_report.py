from odoo import models, fields, api


class ReportBudgetPlanningReport(models.AbstractModel):
    _name = 'report.equip3_agri_operations.budget_planning_report'
    _description = 'Report Budget Planning Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['agriculture.budget.planning'].browse(docids),
            'doc_model': 'agriculture.budget.planning',
        }
