from odoo import models, fields, api


class ShQcTeamTypeInherit(models.Model):
    _inherit = 'sh.qc.team.type'

    pending_qc_total = fields.Integer(
        string='Pending QC Total', compute='_get_qc_total')
    failed_qc_total = fields.Integer(
        string='Failed QC Total', compute='_get_qc_total')
    passed_qc_total = fields.Integer(
        string='Passed QC Total', compute='_get_qc_total')

    def _execute_qc_total(self, fields_name, team_id):
        query = ("""
            SELECT
                sp.id
            FROM stock_picking AS sp
            INNER JOIN stock_move as sm on sp.id = sm.picking_id
            INNER JOIN sh_qc_point as qc_point on qc_point.id = sm.sh_quality_point_id
            INNER JOIN sh_qc_team as qc_team on qc_team.id = qc_point.team
            WHERE %s = True AND qc_team.id = %s
            """ % (fields_name, team_id))

        self.env.cr.execute(query)
        return self.env.cr.fetchall()

    def _get_qc_total(self):
        for rec in self.filtered(lambda x: x.team_id):
            rec.pending_qc_total = len(
                self._execute_qc_total('is_pending_qc', rec.team_id.id))
            rec.failed_qc_total = len(
                self._execute_qc_total('is_qc_fail', rec.team_id.id))
            rec.passed_qc_total = len(
                self._execute_qc_total('is_qc_pass', rec.team_id.id))

    def pending_qc_view(self):
        if self.name == 'Inventory':
            picking = [x[0] for x in self._execute_qc_total(
                'is_pending_qc', self.team_id.id)]
            return {
                'name': 'Pending Quality Checks',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', picking)],
                'res_model': 'stock.picking',
                'context': {'search_default_picking_type': 1},
                'target': 'current',
            }

    def failed_qc_view(self):
        if self.name == 'Inventory':
            picking = [x[0] for x in self._execute_qc_total(
                'is_qc_fail', self.team_id.id)]
            return {
                'name': 'Failed Quality Checks',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', picking)],
                'res_model': 'stock.picking',
                'context': {'search_default_picking_type': 1},
                'target': 'current',
            }

    def passed_qc_view(self):
        if self.name == 'Inventory':
            picking = [x[0] for x in self._execute_qc_total(
                'is_qc_pass', self.team_id.id)]
            return {
                'name': 'Passed Quality Checks',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', picking)],
                'res_model': 'stock.picking',
                'context': {'search_default_picking_type': 1},
                'target': 'current',
            }

    def get_alert_count(self):
        res = super(ShQcTeamTypeInherit, self).get_alert_count()
        for rec in self:
            if rec.name == 'Inventory':
                stage_id = self.env['sh.qc.alert.stage'].search(
                    [('name', '=', 'DONE')])
                rec.alert_count = self.env['sh.quality.alert'].search_count(
                    [('team_id.id', '=', rec.team_id.id), ('stage_id', 'not in', stage_id.ids)])
        return res

    def team_quality_alert_action(self):
        res = super(ShQcTeamTypeInherit, self).team_quality_alert_action()
        if self.name == 'Inventory':
            stage_id = self.env['sh.qc.alert.stage'].search(
                [('name', '=', 'DONE')])
            alert = self.env['sh.quality.alert'].search(
                [('team_id', '=', self.team_id.id), ('stage_id', 'not in', stage_id.ids)])
            return {
                'name': 'Quality Checks',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'domain': [('team_id', '=', self.team_id.id), ('id', 'in', alert.ids)],
                        'res_model': 'sh.quality.alert',
                        'context': {'search_default_control_point': 1, },
                        'target': 'current',
            }
        return res
