from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpPlan(models.Model):
    _name = 'mrp.plan'
    _inherit = ['mrp.plan', 'sh.mrp.qc.reuse']

    move_point_ids = fields.One2many('sh.qc.move.point', 'plan_id', string='Move Points', readonly=True)

    def action_done(self):
        for record in self:
            record.check_mandatory_qc()
        return super(MrpPlan, self).action_done()
