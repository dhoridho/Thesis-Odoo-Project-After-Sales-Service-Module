# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ShMrpQualityCheck(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'sh.mrp.quality.check'
    _description = "MRP Quality Check"
    _rec_name = 'product_id'

    product_id = fields.Many2one("product.product", "Product")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Status', readonly=True, index=True, copy=False, default='draft')

    sh_workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    sh_mrp = fields.Many2one("mrp.production", "Manufacturing")
    sh_date = fields.Date("Date")
    sh_control_point = fields.Char(string="Control Point")
    control_point_id = fields.Many2one("sh.qc.point", string="Control Point")
    sh_norm = fields.Float("Measure")
    qc_type = fields.Selection([('type1', 'Pass Fail'), ('type2', 'Measurement'), (
        'type3', 'Take A picture'), ('type4', 'Text')], 'Type')
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    attachment_ids = fields.Many2many('ir.attachment', string="QC pictures")
    text_message = fields.Text("QC Text")

    def accept(self):
        self.write({'state': 'pass'})

    def reject(self):
        self.write({'state': 'fail'})
