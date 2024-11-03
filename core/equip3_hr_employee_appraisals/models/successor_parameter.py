from odoo import api, fields, models, _


class SuccessorParameter(models.Model):
    _name = "successor.parameter"
    _description = "Sucessor Parameter"

    name = fields.Char(string="Parameter")
    computation_type = fields.Selection(
        [("python_code", "Python Code"), ("matrix", "Matrix")],
        string="Computation Type",
        default="python_code",
    )
    target_object = fields.Char("Target Object")
    python_code = fields.Text(
        string="Python Code",
        compute="_compute_target_object",
        store=True,
        readonly=False,
    )
    matrix_ids = fields.One2many(
        comodel_name="appraisals.matrix.schema",
        inverse_name="successor_parameter_id",
        string="Matrix",
        compute="_compute_matrix_ids",
        store=True,
        readonly=False,
    )
    # sequence = fields.Integer(string="Sequence", default=0)
    # weight = fields.Integer(string="Weight", default=0)

    @api.depends("computation_type")
    def _compute_target_object(self):
        for line in self:
            if line.computation_type == "python_code":
                result = """competency_match = 0\nfor line in self:\
                    \n\tfor suggestion in line.suggestion_comp_match_ids:\
                    \n\t\tif line.current_job.id == suggestion.id:\
                    \n\t\t\tcompetency_match = suggestion.competency_match"""
                line.python_code = result

    @api.depends("target_object")
    def _compute_matrix_ids(self):
        for line in self:
            if line.target_object:
                matrix_model = self.env["appraisals.matrix.schema"]

                valid_object = self.env["ir.model"].search(
                    [("model", "=", line.target_object)]
                )
                if valid_object:
                    if line.target_object == "employee.performance":
                        data_categories = self.env["nine.box.matrix"].search([])
                        for data in data_categories:
                            existing_records = self.env[
                                "appraisals.matrix.schema"
                            ].search([("name", "=", data.category)])
                            if not existing_records:
                                new_matrix_record = matrix_model.create(
                                    {
                                        "name": data.category,
                                        "value": 0,
                                        "model_name": line.target_object,
                                    }
                                )

                                line.matrix_ids = [(4, new_matrix_record.id, 0)]

                            matrix_records = matrix_model.search(
                                [("model_name", "=", line.target_object)]
                            )
                            line.matrix_ids = [(6, 0, matrix_records.ids)]
                else:
                    line.matrix_ids = False
            else:
                line.matrix_ids = False


class AppraisalsMatrixSchema(models.Model):
    _name = "appraisals.matrix.schema"
    _description = "Appraisals Matrix Schema"

    name = fields.Char("Category")
    value = fields.Integer("Value")
    model_name = fields.Char("Model Name")
    successor_parameter_id = fields.Many2one(
        "successor.parameter", string="Successor Parameter"
    )
