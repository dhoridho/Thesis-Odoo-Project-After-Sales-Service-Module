from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    def _get_student_profile_rule_for_teacher(self):
        user = self.env.user
        base_rule = ['|', '&', ('state', '!=', 'done'), ('approved_matrix_ids.user_id', '=', user.id), '&', ('state', '=', 'done')]
        teacher = self.env['school.teacher'].sudo().search([('user_id', '=', user.id)], limit=1)
        if teacher and (teacher.group_class_ids or teacher.subject_id):
            group_class_rule = False
            subject_rule = False
            if teacher.group_class_ids:
                group_class_rule = ['&', ('history_ids.group_class_id', 'in', teacher.group_class_ids.ids), ('history_ids.status', '=', 'active')]
            if teacher.subject_id:
                subject_rule = [('subject_ids', 'in', teacher.subject_id.ids)]

            additional_rule = ['|']
            if group_class_rule and subject_rule:
                additional_rule += subject_rule + group_class_rule
            elif group_class_rule:
                additional_rule = group_class_rule
            elif subject_rule:
                additional_rule = subject_rule
            base_rule += additional_rule
        else:
            base_rule.append((0, '=', 1))
        return base_rule

    def _get_academic_tracking_rule_for_teacher(self):
        teacher = self.env['school.teacher'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        if teacher:
            group_class_students = []
            if teacher.group_class_ids:
                group_class_students = self.env['student.student'].search([('history_ids.group_class_id', 'in', teacher.group_class_ids.ids), ('history_ids.status', '=', 'active')]).ids
            return ['|', ('student_id', 'in', group_class_students), ('all_score_subject_ids.subject_id', 'in', teacher.subject_id.ids)]
        else:
            return [(0, '=', 1)]
