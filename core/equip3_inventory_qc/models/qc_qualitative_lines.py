from odoo import models, fields, api


class QcQualitativeLines(models.Model):
    _name = 'qp.qualitative.lines'
    _description = 'Qc Qualitative Lines'

    sequence = fields.Integer("No")
    item_id = fields.Many2one('qc.checksheet.items', string="Item")
    direction = fields.Char(related='item_id.direction', string="Direction")
    qc_item_dir_id = fields.Many2one('sh.qc.point', string="Qc Item")

    @api.model
    def default_get(self, fields):
        res = super(QcQualitativeLines, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'qualitative_ids' in context_keys:
                if len(self.env.context.get('qualitative_ids')) > 0:
                    next_sequence = len(
                        self.env.context.get('qualitative_ids')) + 1
        res.update({'sequence': next_sequence})
        return res
