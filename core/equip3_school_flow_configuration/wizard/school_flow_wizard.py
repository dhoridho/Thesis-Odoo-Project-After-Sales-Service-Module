from odoo import api, models, fields, _

class SchoolFlowWizard(models.TransientModel):
    _name = 'school.flow.wizard'

    name = fields.Char(string='Name', default='School Flow')

    def button_fee_head(self):
        action = self.env.ref('school_fees.action_student_payslip_line_form').read()[0]
        return action

    def button_fee_structure(self):
        action = self.env.ref('school_fees.action_student_fees_structure_form').read()[0]
        return action

    def button_create_school(self):
        action = self.env.ref('school.action_school_school_form').read()[0]
        return action

    def button_create_program(self):
        action = self.env.ref('school.action_standard_standard_form').read()[0]
        return action
        
    def button_create_intake(self):
        action = self.env.ref('school.action_school_standard_form').read()[0]
        return action

    def button_create_subject(self):
        action = self.env.ref('school.action_subject_subject_form').read()[0]
        return action

    def button_create_admission_approval_matrix(self):
        action = self.env.ref('equip3_school_operation.school_approval_matrix_act_window').read()[0]
        return action

    def button_admission_register(self):
        action = self.env.ref('school.action_student_student_form_2').read()[0]
        return action

    def button_student_invoice(self):
        action = self.env.ref('school_fees.action_student_payslip_form').read()[0]
        return action

    def button_student(self):
        action = self.env.ref('school.action_student_student_form_12').read()[0]
        return action
    
    def button_classes_configuration(self):
        action = self.env.ref('equip3_school_flow_configuration.class_flow_wizard_action').read()[0]
        return action
    
    def button_subject_weightage(self):
        action = self.env.ref('equip3_school_operation.ems_subject_action').read()[0]
        return action

    def button_scoring(self):
        action = self.env.ref('equip3_school_operation.subject_score_action').read()[0]
        return action

    def button_academic_tracking(self):
        action = self.env.ref('equip3_school_operation.academic_tracking_action').read()[0]
        return action

    def button_academic_year(self):
        action = self.env.ref('school.action_academic_year_form').read()[0]
        return action

    def button_term(self):
        action = self.env.ref('school.action_academic_month_form').read()[0]
        return action

