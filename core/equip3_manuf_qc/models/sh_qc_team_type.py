from odoo import models


class ShQcTeamType(models.Model):
    _inherit = 'sh.qc.team.type'

    def team_quality_alert_action(self):
        res = super(ShQcTeamType, self).team_quality_alert_action()
        if isinstance(res, dict):
            res['view_mode'] = 'kanban,tree,form'
            res['context'] = {'search_default_stage': 1}
        return res

    # temporary override due to slow compute 
    # TODO: find effective algorithm for searching pending_qc, qc_fail, and qc_pass
    def get_pending_qc_count(self):
        for rec in self:
            rec.pending_qc_count = 0

    def get_failed_qc_count(self):
        for rec in self:
            rec.failed_qc_count = 0

    def get_passed_qc_count(self):
        for rec in self:
            rec.passed_qc_count = 0

    def get_partially_passed_qc_count(self):
        for rec in self:
            rec.partially_passed_qc_count = 0
