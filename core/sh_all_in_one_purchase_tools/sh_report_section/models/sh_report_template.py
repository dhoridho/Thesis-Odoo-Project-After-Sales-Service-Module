# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ReportTemplate(models.Model):
    _name = "sh.report.template"
    _description = "Report Template"

    name = fields.Char(string="Template Name", required=True)
    section_line = fields.One2many(
        comodel_name="sh.report.section",
        inverse_name="type_id",
        string="Section"
    )

    border_main = fields.Boolean(string="Border")
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
        string="Border Color"
    )
    new_page = fields.Boolean(
        string="New Page",
        alt="Template Print in New Page"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
