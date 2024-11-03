from odoo import fields, models, api, _



class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'


    model = fields.Char('Model')


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'


    operator_id = fields.Many2one('hr.employee','Operator')
    remarks = fields.Text('Remarks')
    report_lot_ids = fields.Many2many('stock.production.lot', compute='_compute_lot_reports')


    @api.model
    def act_work_center_result_report_redirect(self):
        return self.env.ref('equip3_work_center_result_report.tag_work_center_result_report_board').read()[0]

    def _compute_lot_reports(self):
        for record in self:
            lots = record.finished_lot_ids | record.rejected_lot_ids
            record.report_lot_ids = [(6, 0, lots.ids)]
