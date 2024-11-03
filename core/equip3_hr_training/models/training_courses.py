from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class TrainingCourses(models.Model):
    _name = 'training.courses'
    _description = 'Training Courses for Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char(string='Course Name', tracking=True, required=True)
    estimated_cost = fields.Selection(
        [('idr', 'IDR'), ('eur', 'EUR'), ('usd', 'USD')], string='Estimated Cost', tracking=True, default='idr')
    renewable = fields.Integer(string="Renewable Every")
    minimal_score = fields.Float(string='Minimal Score', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    training_category_id = fields.Many2one('training.category', string='Training Category', required=True)
    create_by = fields.Many2one('res.users', 'Created by', default=lambda self: self.env.user)
    create_date = fields.Date('Created on', default=fields.date.today())
    final_score_formula = fields.Text(string='Final Score Formula',
        default='''pretest = (pre_test * 50)/100
posttest = (post_test * 50)/100
total = pretest + posttest''', help='''pretest = pre test variable
pre_test = pre test score
posttest = post test variable
post_test = post test score
total = final score''')
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    stage_ids = fields.One2many('training.courses.stages','course_id')
    color = fields.Integer()
    # is_favorite = fields.Boolean(string="Favorites")
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')
    favorite_user_ids = fields.Many2many('res.users', 'training_course_favorite_user_rel', 'course_id', 'user_id', default=_get_default_favorite_user_ids)
    count_conduct_to_approved = fields.Integer(string="To Approved", compute='_compute_conduct_to_approved')
    count_conduct_on_progress = fields.Integer(string="On Progress", compute='_compute_conduct_on_progress')
    count_conduct_completed = fields.Integer(string="Completed", compute='_compute_conduct_completed')
    
    
    @api.onchange('name')
    def _onchange_name(self):
        for record in self:
            if record.name:
                line_ids = []
                if not record.stage_ids:
                    stage_ids = self.env['training.stages'].search([])
                    for record_stage in stage_ids:
                        line_ids.append((0,0,{'sequence':record_stage.sequence,
                                              'stage_id':record_stage.id
                                              }))
                    record.stage_ids = line_ids
                    
    @api.onchange('stage_ids')
    def _onchange_stage_ids(self):
        for record in self:
            if record.stage_ids:
                if len(record.stage_ids.filtered(lambda line:line.pre_test)) >1:
                    raise ValidationError("Pre-Test Cannot more than one")
                if len(record.stage_ids.filtered(lambda line:line.post_test)) >1:
                    raise ValidationError("Post-Test Cannot more than one")
                if len(record.stage_ids.filtered(lambda line:line.start)) >1:
                    raise ValidationError("Start Stage Cannot more than one")
                if len(record.stage_ids.filtered(lambda line:line.completed)) >1:
                    raise ValidationError("End Stage Cannot more than one")
            
    
    def _compute_is_favorite(self):
        for course in self:
            course.is_favorite = self.env.user in course.favorite_user_ids

    def _inverse_is_favorite(self):
        unfavorited_courses = favorited_courses = self.env['training.courses']
        for course in self:
            if self.env.user in course.favorite_user_ids:
                unfavorited_courses |= course
            else:
                favorited_courses |= course
        favorited_courses.write({'favorite_user_ids': [(4, self.env.uid)]})
        unfavorited_courses.write({'favorite_user_ids': [(3, self.env.uid)]})

    def _get_conduct_to_approve_stage(self):
        self.ensure_one()
        approve_stage_ref = self.env.ref('equip3_hr_training.course_stage_7').id
        return self.env['training.courses.stages'].search([
            ('course_id', '=', self.id),
            ('stage_id', '=', approve_stage_ref)], limit=1)

    def _compute_conduct_to_approved(self):
        for course in self:
            course.count_conduct_to_approved = self.env["training.conduct"].search_count(
                [("course_id", "=", course.id), ("stage_course_id", "=", course._get_conduct_to_approve_stage().id)]
            )

    def _get_conduct_on_progress_stage(self):
        self.ensure_one()
        approve_stage_ref = self.env.ref('equip3_hr_training.course_stage_3').id
        return self.env['training.courses.stages'].search([
            ('course_id', '=', self.id),
            ('stage_id', '=', approve_stage_ref)], limit=1)

    def _compute_conduct_on_progress(self):
        for course in self:
            course.count_conduct_on_progress = self.env["training.conduct"].search_count(
                [("course_id", "=", course.id), ("stage_course_id", "=", course._get_conduct_on_progress_stage().id)]
            )

    def _get_conduct_completed_stage(self):
        self.ensure_one()
        approve_stage_ref = self.env.ref('equip3_hr_training.course_stage_4').id
        return self.env['training.courses.stages'].search([
            ('course_id', '=', self.id),
            ('stage_id', '=', approve_stage_ref)], limit=1)

    def _compute_conduct_completed(self):
        for course in self:
            course.count_conduct_completed = self.env["training.conduct"].search_count(
                [("course_id", "=", course.id), ("stage_course_id", "=", course._get_conduct_completed_stage().id)]
            )

    def create_training_conduct(self):
        return {
            'name': _("Training Conduct"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_hr_training.form_training_conduct').id,
            'res_model': 'training.conduct',
            'type': 'ir.actions.act_window',
            'context': {'default_course_id': self.id},
        }


    
class TrainingCourseStages(models.Model):
    _name = 'training.courses.stages'
    _rec_name = 'stage_id'
    _order = 'sequence'
    
    sequence = fields.Integer()
    course_id = fields.Many2one('training.courses',ondelete='cascade')
    stage_id = fields.Many2one('training.stages')
    is_default_stages = fields.Boolean('Cannot be delete or edit', related='stage_id.is_default_stages')
    survey_pre_test_id = fields.Many2one('survey.survey')
    survey_post_test_id = fields.Many2one('survey.survey')
    pre_test = fields.Boolean()
    post_test = fields.Boolean()
    start = fields.Boolean()
    completed = fields.Boolean() 
    fold = fields.Boolean(related='stage_id.fold')    
    remark =  fields.Text()
    
    
    
    @api.onchange('pre_test','post_test')
    def _onchange_pre_post_test_(self):
        for record in self:
            if record.pre_test:
                if record.post_test:
                    record.post_test = False
                    record.pre_test = False
