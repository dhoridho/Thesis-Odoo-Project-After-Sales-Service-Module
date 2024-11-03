from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AppraisalsSuccessionPlanning(models.Model):
    _name = "appraisals.succession.planning"
    _description = "Appraisals Sucession Planning"

    name = fields.Char(string="Sueccession Planning")
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position")
    successor_template_id = fields.Many2one(
        comodel_name="successor.parameter.template", string="Successor Template"
    )
    position_holder_ids = fields.One2many(
        comodel_name="appraisals.position.holder",
        inverse_name="succession_planning_id",
        string="Position Holder",
        compute="_compute_succession_planning",
        store=True,
    )
    successor_candidate_ids = fields.One2many(
        comodel_name="appraisals.successor.candidate",
        inverse_name="succession_planning_id",
        string="Successor Candidate",
        compute="_compute_succession_planning",
        store=True,
    )
    show_find_successor = fields.Boolean(
        string='Show Find Successor',
        default=False
    )
    is_generated = fields.Boolean(
        string='Is Generated',
        default=False
    )

    @api.model
    def create(self, values):
        values['show_find_successor'] = True
        return super(AppraisalsSuccessionPlanning, self).create(values)
    
    def read(self, fields=None, load='_classic_read'):
        result = super(AppraisalsSuccessionPlanning, self).read(fields=fields, load=load)
        if 'successor_candidate_ids' in fields:
            for record in result:
                if 'successor_candidate_ids' in record:
                    record['successor_candidate_ids'] = record['successor_candidate_ids'][:5]

        if 'position_holder_ids' in fields:
            for record in result:
                if 'position_holder_ids' in record:
                    record['position_holder_ids'] = record['position_holder_ids'][:5]
        return result

    def action_find_successor_candidate(self):
        for line in self:
            if line.job_id and line.successor_template_id:
                # Get Successer Candidates
                processed_candidate_names = set()
                successor_candidate_records = []

                hr_employees = self.env["hr.employee"].search([
                    ("job_id.id", "!=", line.job_id.id)
                ])
                suggestions_competencies_candidadte = self.env["employee.career.suggestion"].search(
                    [("current_job.id", "!=", line.job_id.id)], 
                    order="create_date desc",
                )
                parameter_templates_candidate = self.env["successor.parameter.template"].search([
                    ("id", "=", line.successor_template_id.id)
                ], limit=1)

                target_score = parameter_templates_candidate.total_weight
                
                for employee in hr_employees:
                    for suggestion_comp_candidate in suggestions_competencies_candidadte:
                        if employee.id == suggestion_comp_candidate.name.id:
                            if suggestion_comp_candidate.name.id not in processed_candidate_names:
                                current_score_candidate = 0
                                
                                if not suggestion_comp_candidate.suggestion_comp_match_ids:
                                    current_score_candidate = 0
                                else:
                                    for suggestion_candidate in suggestion_comp_candidate.suggestion_comp_match_ids:
                                        if suggestion_comp_candidate.current_job.id == suggestion_candidate.job_id.id:
                                            processed_candidate_names.add(suggestion_comp_candidate.name.id)
                                            competency_match_candidate = suggestion_candidate.competency_match
                                            weight_score_candidate = 0
                                            competency_match_id = self.env.ref('equip3_hr_employee_appraisals.successor_parameter_master_1').id
                                            
                                            for parameter_candidate in parameter_templates_candidate.successor_parameter_template_line_ids:
                                                if parameter_candidate.successor_parameter_id.id == competency_match_id:
                                                    weight_score_candidate += parameter_candidate.weight
                                            
                                            current_score_candidate += (competency_match_candidate * weight_score_candidate) / target_score
                                            
                                employee_performances_candidate = self.env["employee.performance"].search([
                                    ("state", "=", "done"),
                                    ("n_grid_result_id", "!=", False),
                                    ("employee_id", "=", employee.id)
                                ])
                                nba_id = self.env.ref('equip3_hr_employee_appraisals.successor_parameter_master_8').id
                                
                                for emp_performance_candidate in employee_performances_candidate:
                                    for template_candidate in line.successor_template_id:
                                        for parameter_template_candidate in template_candidate.successor_parameter_template_line_ids:
                                            if parameter_template_candidate.successor_parameter_id.id == nba_id:
                                                for nba_candidate in parameter_template_candidate.successor_parameter_id:
                                                    for matrix_candidate in nba_candidate.matrix_ids:
                                                        if matrix_candidate.name == emp_performance_candidate.n_grid_result_id.category:
                                                            calculate_score_candidate = (matrix_candidate.value * parameter_template_candidate.weight) / target_score
                                                            current_score_candidate += calculate_score_candidate
                                                            
                                successor_candidate_data = {
                                    "name": suggestion_comp_candidate.name.id,
                                    "job_id": suggestion_comp_candidate.current_job.id,
                                    "email": suggestion_comp_candidate.name.work_email,
                                    "target_score": target_score,
                                    "current_score": current_score_candidate,
                                }
                                successor_candidate_records.append(successor_candidate_data)
                                processed_candidate_names.add(suggestion_comp_candidate.name.id)

                
                created_successor_candidates = self.env["appraisals.successor.candidate"].create(
                    successor_candidate_records
                )
                line.successor_candidate_ids = [(6, 0, created_successor_candidates.ids)]
                line.is_generated = True


    @api.depends("job_id", "successor_template_id")
    def _compute_succession_planning(self):
        for line in self:
            # Get Job Position Holders
            if line.job_id and line.successor_template_id:
                suggestions_competencies = self.env["employee.career.suggestion"].search(
                    [("current_job.id", "=", line.job_id.id)], 
                    order="create_date desc",
                )
                job_position_holder_records = []
                job_position_holder_detail_records = []
                processed_names = set()
                competency_match = 0
                weight_score = 0

                parameter_templates = self.env["successor.parameter.template"].search([
                    ("id", "=", line.successor_template_id.id)
                ], limit=1)

                parameter_names = []
                for parameter in parameter_templates.successor_parameter_template_line_ids:
                    if parameter.weight > 0:
                        parameter_names.append(parameter.successor_parameter_id.name)

                for suggestion_comp in suggestions_competencies:
                    string_values = []
                    numeric_values = []
                    emlpoyee_names = []
                    if suggestion_comp.name.id not in processed_names:
                        processed_names.add(suggestion_comp.name.id)
                        current_score = 0
                        found_matching_suggestion = False
                        for suggestion in suggestion_comp.suggestion_comp_match_ids:
                            if suggestion_comp.current_job.id == suggestion.job_id.id:
                                found_matching_suggestion = True
                                competency_match = suggestion.competency_match
                                competency_match_id = self.env.ref('equip3_hr_employee_appraisals.successor_parameter_master_1').id
                                is_numeric = isinstance(competency_match, int) or isinstance(competency_match, float)
                                if is_numeric:
                                    numeric_values.append(competency_match)
                                    string_values.append("-")

                                for parameter in parameter_templates.successor_parameter_template_line_ids:
                                    if parameter.successor_parameter_id.id == competency_match_id:
                                        weight_score += parameter.weight
                                        current_score += (competency_match * weight_score) / parameter_templates.total_weight
                                        print(f">>>>>>>>> emp: {suggestion_comp.name.name} - comp: {competency_match} - score: {current_score}")

                        if not found_matching_suggestion:
                            processed_names.add(suggestion_comp.name.id)
                            numeric_values.append(0.0)
                            string_values.append("-")
                            print(f">>>>>>>>> emp: {suggestion_comp.name.name} - comp: {competency_match} - score: {current_score}")
                        
                        if parameter_templates.total_weight == 0:
                            raise ValidationError("The total of parameter weight cannot be zero, please define weight for each parameters")

                        emlpoyee_names.append(suggestion_comp.name.name)
                        
                        employee_performances = self.env["employee.performance"].search([
                            ("state", "=", "done"),
                            ("n_grid_result_id", "!=", False),
                            ("employee_id", "=", suggestion_comp.name.id)
                        ])
                        nba_id = self.env.ref('equip3_hr_employee_appraisals.successor_parameter_master_8').id

                        if not employee_performances:
                            string_values.append("-")
                            numeric_values.append(0.0)

                        for emp_performance in employee_performances:
                            for template in line.successor_template_id:
                                for parameter_template in template.successor_parameter_template_line_ids:
                                    if parameter_template.successor_parameter_id.id == nba_id:
                                        for nba in parameter_template.successor_parameter_id:
                                            for matrix in nba.matrix_ids:
                                                if matrix.name == emp_performance.n_grid_result_id.category:
                                                    if isinstance(matrix.name, str):
                                                        string_values.append(matrix.name)
                                                        numeric_values.append(0.0)
                                                    calculate_score = (matrix.value * parameter_template.weight) / template.total_weight
                                                    print(f">>>>>>>>> emp1: {suggestion_comp.name.name} - ninebox: {matrix.name} - score: {calculate_score} - current_score: {current_score}")
                                                    current_score += calculate_score
                        
                        job_position_holder_data = {
                            "name": suggestion_comp.name.id,
                            "job_id": line.job_id.id,
                            "email": suggestion_comp.name.work_email,
                            "current_score": current_score,
                        }
                        job_position_holder_records.append(job_position_holder_data)
                        job_pos_holder_details = {
                            "name": parameter_names,
                            "value_str": string_values,
                            "value_number": numeric_values,
                        }
                        job_position_holder_detail_records.append(job_pos_holder_details)
                        

                created_position_holders = self.env["appraisals.position.holder"].create(
                    job_position_holder_records
                )
                line.position_holder_ids = [(6, 0, created_position_holders.ids)]

                for detail in job_position_holder_detail_records:
                    position_holder = created_position_holders

                    # Create a list of tuples to add to the One2many field
                    position_holder_parameter_results = []
                    for i in range(len(detail["name"])):
                        parameter_result_data = {
                            'name': detail['name'][i],
                            'value_str': detail['value_str'][i],
                            'value_number': detail['value_number'][i],
                        }
                        position_holder_parameter_results.append((0, 0, parameter_result_data))

                    position_holder.write({'position_holder_parameter_result_ids': position_holder_parameter_results})

class AppraisalsPositionHolder(models.Model):
    _name = "appraisals.position.holder"
    _description = "Appraisals Position Holder"

    name = fields.Many2one(comodel_name="hr.employee", string="employee")
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position")
    email = fields.Char(string="Email")
    current_score = fields.Float(string="Current Score")
    succession_planning_id = fields.Many2one(
        comodel_name="appraisals.succession.planning", string="Sueccession Planning"
    )
    position_holder_parameter_result_ids = fields.One2many(
        comodel_name='position.holder.parameter.result',
        inverse_name='position_holder_id', 
        string='Position Holder Parameter Result'
    )


class AppraisalsSuccessorCandidate(models.Model):
    _name = "appraisals.successor.candidate"
    _description = "Appraisals Successor Candidate"

    name = fields.Many2one(comodel_name="hr.employee", string="employee")
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position")
    email = fields.Char(string="Email")
    current_score = fields.Float(string="Current Score")
    target_score = fields.Float(string="Target Score")
    succession_planning_id = fields.Many2one(
        comodel_name="appraisals.succession.planning", string="Sueccession Planning"
    )
    


class AppraisalsSuccessorParameterResult(models.Model):
    _name = "position.holder.parameter.result"
    _description = "Position Holder Parameter Result"

    name = fields.Char("Parameter")
    value_str = fields.Char("Value String")
    value_number = fields.Float("Value")
    position_holder_id = fields.Many2one(
        comodel_name='appraisals.position.holder',
        string='Position Holder'
    )
    position_holder_wizard_id = fields.Many2one(
        comodel_name='job.position.holder.wizard',
        string='Position Holder Wizard'
    )
