from odoo import models, fields, api


class QpQuantitativeLines(models.Model):
    _name = 'qp.quantitative.lines'
    _description = 'Qp Quantitative Lines'

    sequence = fields.Integer("No")
    dimansion_id = fields.Many2one('checksheet.dimensions', string="Dimensions")
    norm_qc = fields.Float(string="Norm")
    tolerance_from_qc = fields.Float(string="Tolerance From")
    tolerance_to_qc = fields.Float(string="Tolerance To")
    qc_point_id = fields.Many2one('sh.qc.point', string="Qc Point")

    @api.model
    def default_get(self, fields):
        res = super(QpQuantitativeLines,self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'quantitative_ids' in context_keys:
                if len(self.env.context.get('quantitative_ids')) > 0:
                    next_sequence = len(self.env.context.get('quantitative_ids')) + 1
        res.update({'sequence': next_sequence})
        return res


    @api.constrains('norm_qc', 'tolerance_from_qc', 'tolerance_to_qc')
    def check_values(self):
        for record in self:
            if record.norm_qc == 0 or record.tolerance_from_qc == 0 or record.tolerance_to_qc == 0:
                raise ValidationError("Norm, Tolerance From and Tolerance To Must Be greater then Zero.")
            if record.norm_qc <= record.tolerance_from_qc:
                raise ValidationError("Tolerance From Must Be less then Norm.")
            if record.norm_qc >= record.tolerance_to_qc:
                raise ValidationError("Tolerance To Must Be greater then Norm.")
