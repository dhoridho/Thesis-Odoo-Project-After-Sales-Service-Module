# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sample_qc = fields.Integer(string="Sample Per Batch", default=1)

    @api.constrains('sample_qc')
    def _check_sample_qc(self):
        for record in self:
            if record.sample_qc <= 0:
                raise ValidationError("Sample Per Batch must be greater then zero.")
