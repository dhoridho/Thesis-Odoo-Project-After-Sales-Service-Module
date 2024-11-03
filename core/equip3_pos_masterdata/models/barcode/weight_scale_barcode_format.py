# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class WeightScaleBarcodeFormat(models.Model):
    _name = "weight.scale.barcode.format"

    name = fields.Char("Name")
    line_ids = fields.One2many('weight.scale.barcode.format.line','parent_id','Lines')
    total_digit = fields.Integer('Total Digit',compute='_compute_total_digit',store=False)

    def _compute_total_digit(self):
        for data in self:
            total_digit = 0
            for data_line in data.line_ids:
                total_digit += data_line.digit
            data.total_digit = total_digit

    @api.constrains('line_ids')
    def check_line_ids(self):
        for data in self:
            if len(data.line_ids) <= 1:
                raise UserError("Please setline more than one.")


class WeightScaleBarcodeFormatLine(models.Model):
    _name = "weight.scale.barcode.format.line"
    _order = 'parent_id, sequence, id'

    name = fields.Char("Name")
    parent_id = fields.Many2one('weight.scale.barcode.format','Parent')
    digit = fields.Integer('Digit',default=1,required=1)
    sequence = fields.Integer('Sequence',default=1)
    data =  fields.Selection([
        ('None', 'None'),
        ('Product Code', 'Product Code'),
        ('Weight', 'Weight'),
        ('Price', 'Price')
    ], string='Data', default='None',required=1)
    coefficient_ratio = fields.Float('Coefficient Ratio',digits=(5,5),default=1)

    @api.constrains('digit')
    def check_digit(self):
        for data in self:
            if data.digit <= 0:
                raise UserError("Please set digit more than zero.")

    @api.onchange('digit','data')
    def onchange_digit_n_data(self):
        self.name = str(self.digit)+' Digit ('+self.data+')'