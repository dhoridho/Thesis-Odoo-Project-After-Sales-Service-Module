from odoo import fields, models, api


class passNextStageWizard(models.TransientModel):
    _name = 'pass.next.stage.wizard'
    
    job_ids = fields.Many2many('hr.job')
    stage_ids = fields.Many2many('hr.recruitment.stage')
    applicant_ids = fields.Many2many('hr.applicant')
    
    
    def submit(self):
        if self.applicant_ids:
            for record in self.applicant_ids:
                record.pass_to_next_stage()
            
    
    
    @api.onchange('job_ids','stage_ids')
    def _onchange_job_ids_stage_ids(self):
        query_params = []
        query_statement = ""
        if self.job_ids and not self.stage_ids:
           column = "job_id"
           job_ids = self.job_ids.ids
           query_statement = f"SELECT id FROM hr_applicant WHERE {column} IN %s"
           query_params.append(tuple(job_ids))
        if self.stage_ids and not self.job_ids:
           column = "stage_id"
           stage_ids = self.stage_ids.ids
           query_statement = f"SELECT id FROM hr_applicant WHERE {column} IN  %s"
           query_params.append(tuple(stage_ids))
        if self.job_ids and self.stage_ids:
            column_job = "job_id"
            job_ids = self.job_ids.ids
            column_stage = "stage_id"
            stage_ids = self.stage_ids.ids
            query_statement = f"SELECT id FROM hr_applicant WHERE {column_job} IN %s and {column_stage} in %s"
            query_params.append(tuple(job_ids))
            query_params.append(tuple(stage_ids))
            
        if query_statement:
            self.env.cr.execute(query_statement, query_params)
            raw_applicant_ids = self._cr.fetchall()
            idlist = [id[0] for id in raw_applicant_ids]
            self.applicant_ids = [(6, 0, idlist)]