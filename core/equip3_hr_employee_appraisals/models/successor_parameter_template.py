from odoo import api, fields, models, _


class SuccessorgParameterTemplate(models.Model):
    _name = "successor.parameter.template"
    _description = "Sucessor Parameter Template"

    name = fields.Char(string="Template")
    total_weight = fields.Integer(
        string="Total Weight", compute="compute_total_weight", store=True
    )
    successor_parameter_template_line_ids = fields.One2many(
        string="Successor Parameter Template Line",
        comodel_name="successor.parameter.template.line",
        inverse_name="sucessor_parameter_template_id",
        store=True,
        readonly=False,
    )

    @api.depends("successor_parameter_template_line_ids.weight")
    def compute_total_weight(self):
        for record in self:
            total_weight = sum(
                record.successor_parameter_template_line_ids.mapped("weight")
            )
            record.total_weight = total_weight


class SuccessorgParameterTemplateLine(models.Model):
    _name = "successor.parameter.template.line"
    _description = "Sucessor Parameter Template Line"

    successor_parameter_id = fields.Many2one(
        string="Successor Parameter", comodel_name="successor.parameter"
    )
    weight = fields.Integer(
        string="Weight",
        readonly=False,
    )
    sucessor_parameter_template_id = fields.Many2one(
        string="Sucessor Parameter Template",
        comodel_name="successor.parameter.template",
        ondelete="cascade",
    )

