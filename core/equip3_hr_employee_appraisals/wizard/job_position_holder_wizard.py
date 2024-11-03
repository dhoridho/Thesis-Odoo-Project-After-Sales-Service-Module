from odoo import fields, models, api


class JobPositionHolderWizard(models.Model):
    _name = "job.position.holder.wizard"
    _description = "Job Position Holder Wizard"

    name = fields.Many2one(comodel_name="hr.employee", string="Name")
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position")
    email = fields.Char("Email")
    current_score = fields.Float("Current Score")
    position_holder_parameter_wizard_ids = fields.One2many(
        comodel_name='position.holder.parameter.result',
        inverse_name='position_holder_wizard_id', 
        string='Position Holder Parameter Result'
    )
    
    @api.model
    def default_get(self, fields):
        res = super(JobPositionHolderWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')

        if active_id:
            job_pos_holder_id = self.env["appraisals.position.holder"].sudo().browse(active_id)
            res.update({
                "name": job_pos_holder_id.name.id,
                "job_id": job_pos_holder_id.job_id.id,
                "email": job_pos_holder_id.email,
                "current_score": job_pos_holder_id.current_score,
            })

            if 'position_holder_parameter_wizard_ids' in fields:
                parameter_result_values = []
                for parameter_result in job_pos_holder_id.position_holder_parameter_result_ids:
                    parameter_result_data = {
                        'name': parameter_result.name,
                        'value_str': parameter_result.value_str,
                        'value_number': parameter_result.value_number,
                    }
                    parameter_result_values.append((0, 0, parameter_result_data))

                res.update({
                    "position_holder_parameter_wizard_ids": parameter_result_values,
                })

        return res
