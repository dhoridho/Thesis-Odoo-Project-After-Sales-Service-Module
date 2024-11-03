from odoo import fields, models, api


class SuccessorCandidate(models.TransientModel):
    _name = "successor.candidate.wizard"
    _description = "Successor Candidate Wizard"

    name = fields.Many2one(comodel_name="hr.employee", string="Name")
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position")
    email = fields.Char("Email")
    current_score = fields.Float("Current Score")
    # position_holder_parameter_wizard_ids = fields.One2many(
    #     comodel_name='position.holder.parameter.result',
    #     inverse_name='position_holder_wizard_id', 
    #     string='Position Holder Parameter Result'
    # )
    
    @api.model
    def default_get(self, fields):
        res = super(SuccessorCandidate, self).default_get(fields)
        active_id = self.env.context.get('active_id')

        if active_id:
            successor_candidate_id = self.env["appraisals.successor.candidate"].sudo().browse(active_id)
            res.update({
                "name": successor_candidate_id.name.id,
                "job_id": successor_candidate_id.job_id.id,
                "email": successor_candidate_id.email,
                "current_score": successor_candidate_id.current_score,
            })

        return res
