# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ReportSection(models.Model):
    _name = "sh.report.section"
    _description = "Report Template"

    name = fields.Char(string="Section Title", required=True)
    type = fields.Selection([
        ('text', 'Plain Text'),
        ('html', 'Html')
        ], default="text",
        string="Section Type",
        required=True
    )

    content_text = fields.Text(string="Text")
    content_html = fields.Html(string="HTML")

    type_id = fields.Many2one(comodel_name="sh.report.template")
    check_ids = fields.Many2many(
        comodel_name="sh.edit.title",
        string="Title Style"
    )
    text_size = fields.Integer(
        string="Text Size",
        required=True,
        default="16",
        size=2,
        help="Font size in pixel"
    )
    color = fields.Char(string="Background Color")
    borders = fields.Boolean(string="Border")
    border_size = fields.Integer(
        required=True,
        size="2",
        default="2",
        string="Border Size"
    )
    border_style = fields.Selection([
        ('solid', 'Solid'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('ridge', 'Ridge'),
        ('groove', 'Groove')
        ],
        default="solid",
        string="Border Type",
        required=True
    )
    border_color = fields.Char(
        required=True,
        default="#000000",
        strnig="Border Color"
    )
    
