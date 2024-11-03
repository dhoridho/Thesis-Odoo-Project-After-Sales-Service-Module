from odoo import _, api, fields, models
from calendar import Calendar
from datetime import date, datetime
from odoo.exceptions import ValidationError


class ProgressiveMilestoneTerm(models.Model):
    _name = 'progressive.milestone.term'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Progressive Milestone Term'

    name = fields.Char(string='Name', required=True, copy=False, index=True)
    milestone_term_ids = fields.One2many('milestone.term.const', 'milestone_id', string="Milestone and Term")
    
    @api.constrains('milestone_term_ids')
    def _constrains_milestone_type(self):
        total_progress = 0.0
        progress_flag = False
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                progress_flag = True
                total_progress = line.claim_percentage

        if total_progress < 100.00 and progress_flag:
            raise ValidationError(
                _("Your Progress has a Contract Term less than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))


    @api.onchange('milestone_term_ids')
    def _onchange_milestone_type(self):
        last_progress = 0.0
        current_progress = 0.0
        last_progress_name = ""
        current_progress_name = ""
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                if current_progress >= 100:
                    raise ValidationError(_("Your Progress has been 100%, you can't add more Progress."))
                if line.claim_percentage:
                    last_progress = current_progress
                    last_progress_name = current_progress_name
                    current_progress = line.claim_percentage
                    current_progress_name = line.name
                    if current_progress <= last_progress:
                        raise ValidationError(_("Contract Term of %s can not less than %s, please re-input the Contract Term to bigger than %s%%") % (current_progress_name, last_progress_name, last_progress))
            
        if current_progress > 100.00:
                raise ValidationError(
                    _("Your Progress has a Contract Term more than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))

        
class MilestoneTerm(models.Model):
    _name = 'milestone.term.const'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Milestone and Terms'
    _order = 'sequence'

    @api.depends('milestone_id.milestone_term_ids', 'milestone_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.milestone_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    milestone_id = fields.Many2one('progressive.milestone.term', string="Milestone ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type')
    claim_percentage = fields.Float(string="Contract Terms")

    @api.onchange('type_milestone')
    def onchange_type(self):
        for res in self:
            if res.type_milestone == 'retention1' or res.type_milestone == 'retention2':
                self.write({'claim_percentage': 100})


class ProjectSale(models.Model):
    _inherit = 'project.project'

    # custom claim
    is_set_custom_claim = fields.Boolean(string='Set Contract Custom Claim', default=True, store=True)
    notification_claim = fields.Many2many('res.users', 'notif_claim_partner_rel', 'notif_id', 'user_id', string='Notification Claim Users')

    @api.onchange('is_set_custom_claim')
    def _onchange_set_custom_claim(self):
        if self.is_set_custom_claim:
            self.notification_claim = [(6, 0, [user.id for user in self.project_director])]

    @api.onchange('project_director')
    def _onchange_set_custom_claim_2(self):
        if self.project_director:
            self.notification_claim = [(6, 0, [user.id for user in self.project_director])]


class SaleOrderConstInherit(models.Model):
    _inherit = 'sale.order.const'

    is_set_custom_claim = fields.Boolean(string='Set Contract Custom Claims', store=True, related='project_id.is_set_custom_claim')
    claim_type = fields.Selection([
        ('no_custom', 'No Custom'),
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
        ], string='Based On', default='no_custom')
    progressive_milestone_term_id = fields.Many2one('progressive.milestone.term', string='Milestone and Contract Term Template')
    milestone_term_ids = fields.One2many('sale.milestone.term.const', 'order_id', string="Milestone and Term")
    
    start_month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ])

    start_date_year = fields.Integer('Start Date Year', store=True, compute='_compute_start_date_year')
    end_date_year = fields.Integer('End Date Year', store=True, compute='_compute_end_date_year')
    start_year = fields.Many2one('const.year', string='Year')

    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
    ], default='date')

    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ])

    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ])

    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ])

    repeat_time = fields.Selection([
        (str(i), str(i)+'.00') for i in range(0, 24)
    ], string="Time", default=0)

    is_create_automatically = fields.Boolean(string='Create Automatically', default=True)

    @api.depends('end_date')
    def _compute_end_date_year(self):
        for record in self:
            record.end_date_year = 0
            if record.end_date:
                end_year = int(record.end_date.strftime('%Y'))
                record.end_date_year = end_year
                if record.start_date:
                    start_year = int(record.start_date.strftime('%Y'))
                    for i in range(start_year, end_year+1):
                        year = self.env['const.year'].search([('name', '=', i)])
                        if len(year) < 1:
                            self.env['const.year'].create({'name': i})

    @api.depends('start_date')
    def _compute_start_date_year(self):
        for record in self:
            record.start_date_year = 0
            if record.start_date:
                start_year = int(record.start_date.strftime('%Y'))
                record.start_date_year = start_year
                if record.end_date:
                    end_year = int(record.end_date.strftime('%Y'))
                    for i in range(start_year, end_year+1):
                        year = self.env['const.year'].search([('name', '=', i)])
                        if len(year) < 1:
                            self.env['const.year'].create({'name': i})
    
    # @api.constrains('start_month', 'start_year')
    # def _constraint_start_month(self):
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year:
    #             if rec.start_date and rec.end_date:
    #                 start = rec.start_date
    #                 end = rec.end_date
    #                 start_year = int(start.strftime('%Y'))
    #                 end_year = int(end.strftime('%Y'))
    #                 start_month = int(start.strftime('%m'))
    #                 end_month = int(end.strftime('%m'))
    #                 if start_year == int(rec.start_year.name) and start_month > month_dict[rec.start_month]:
    #                     raise ValidationError(_(f"First claim month can't be before planned start date. Please re-set"))
    #                 elif end_year == int(rec.start_year.name) and end_month < month_dict[rec.start_month]:
    #                     raise ValidationError(_(f"First claim month can't be after planned end date. Please re-set"))
                    
    # @api.constrains('repeat_day', 'repeat_on_month', 'start_month', 'start_year')
    # def _constraint_repeat_day(self):
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year and rec.start_month and rec.repeat_on_month == "date":
    #             start = rec.start_date
    #             end = rec.end_date
    #             start_year = int(start.strftime('%Y'))
    #             end_year = int(end.strftime('%Y'))
    #             start_month = int(start.strftime('%m'))
    #             end_month = int(end.strftime('%m'))
    #             start_day = int(start.strftime('%d'))
    #             end_day = int(end.strftime('%d'))
    #             if start_year == int(rec.start_year.name) and start_month == month_dict[rec.start_month] \
    #                 and int(rec.repeat_day) < start_day:
    #                 raise ValidationError(_(f"First claim date can't be before planned start date. Please re-set"))
    #             elif end_year == int(rec.start_year.name) and end_month == month_dict[rec.start_month] \
    #                 and int(rec.repeat_day) > end_day:
    #                 raise ValidationError(_(f"First claim date can't be after planned end date. Please re-set"))             
    
    # @api.constrains('repeat_weekday', 'repeat_week', 'repeat_on_month', 'start_month', 'start_year')
    # def _constraint_repeat_weekday(self):
    #     week_add_dict = {
    #         "first": 0, "second": 7, "third": 14, "last": 21
    #     }
    #     weekday_dict = {
    #         "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
    #     }
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year and rec.start_month and rec.repeat_on_month == "day":
    #             start = rec.start_date
    #             end = rec.end_date
    #             dates = [d for d in Calendar(6).itermonthdates(int(rec.start_year.name), month_dict[rec.start_month])]
    #             date_num = week_add_dict[rec.repeat_week] + weekday_dict[rec.repeat_weekday]
    #             first_claim_date = dates[date_num]
    #             if first_claim_date < start:
    #                 raise ValidationError(_(f"First claim date can't be before planned start date. Please re-set"))
    #             elif first_claim_date > end:
    #                 raise ValidationError(_(f"First claim date can't be after planned end date. Please re-set"))
    
    
    @api.constrains('milestone_term_ids')
    def constrains_milestone(self):
        for term in self:
            if term.claim_type == 'milestone':
                number_of_lines = len(term.milestone_term_ids)
                if number_of_lines == 0:
                    raise ValidationError(
                        _("You haven't set your milestone, please set it first."))
                for milestone in term.milestone_term_ids:
                    if milestone.type_milestone == "down_payment":
                        if not term.down_payment:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention1":
                        if not term.retention1:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention2":
                        if not term.retention2:
                            milestone.unlink()

    @api.constrains('milestone_term_ids')
    def _constrains_milestone_type(self):
        total_progress = 0.0
        progress_flag = False
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                progress_flag = True
                total_progress = line.claim_percentage
            
        if total_progress < 100.00 and progress_flag:
            raise ValidationError(
                _("Your Progress has a Contract Term less than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))

        
    @api.onchange('milestone_term_ids')
    def _onchange_milestone_type(self):
        last_progress = 0.0
        current_progress = 0.0
        last_progress_name = ""
        current_progress_name = ""
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                if current_progress >= 100:
                    raise ValidationError(_("Your Progress has been 100%, you can't add more Progress."))
                if line.claim_percentage:
                    last_progress = current_progress
                    last_progress_name = current_progress_name
                    current_progress = line.claim_percentage
                    current_progress_name = line.name
                    if current_progress <= last_progress:
                        raise ValidationError(_("Contract Term of %s can not less than %s, please re-input the Contract Term to bigger than %s%%") % (current_progress_name, last_progress_name, last_progress))
            
        if current_progress > 100.00:
                raise ValidationError(
                    _("Your Progress has a Contract Term more than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))

    
    @api.onchange('progressive_milestone_term_id')
    def _onchange_progressive_milestone_term_id(self):
        self.milestone_term_ids = [(5, 0, 0)]
        if self.progressive_milestone_term_id:
            miles = self.progressive_milestone_term_id
            for terms in miles.milestone_term_ids:
                milestone_type = terms.type_milestone
                if milestone_type == 'down_payment':
                    if not self.down_payment:
                        continue
                elif milestone_type == 'retention1':
                    if not self.retention1:
                        continue
                elif milestone_type == 'retention2':
                    if not self.retention2:
                        continue
                self.milestone_term_ids = [(0, 0, {
                    'name': terms.name,
                    'type_milestone': terms.type_milestone,
                    'claim_percentage': terms.claim_percentage,
                })]


    @api.onchange('vo_payment_type', 'contract_parent')
    def onchange_vo_payment_type_12(self):
        if self.vo_payment_type == 'split':
            # self.claim_type = False
            self.progressive_milestone_term_id = False
            self.milestone_term_ids = False
            self.repeat_day = False
            self.repeat_week = False
            self.repeat_weekday = False
            self.repeat_time = False
        elif self.vo_payment_type == 'join':
            if self.contract_parent:
                join = self.contract_parent
                self.claim_type = join.claim_type
                self.progressive_milestone_term_id = join.progressive_milestone_term_id
                self.repeat_on_month = join.repeat_on_month
                self.repeat_day = join.repeat_day
                self.repeat_week = join.repeat_week
                self.repeat_weekday = join.repeat_weekday
                self.repeat_time = join.repeat_time
                self.is_create_automatically = join.is_create_automatically

                for terms_sale in join.milestone_term_ids:
                    self.milestone_term_ids = [(0, 0, {
                        'name': terms_sale.name,
                        'type_milestone': terms_sale.type_milestone,
                        'claim_percentage': terms_sale.claim_percentage,
                    })]
    
    @api.onchange('is_set_custom_claim')
    def _onchange_is_set_custom_claim(self):
        if self.is_set_custom_claim == False:
            # self.claim_type = False
            self.progressive_milestone_term_id = False
            self.milestone_term_ids = False
            self.repeat_day = False
            self.repeat_week = False
            self.repeat_weekday = False
            self.repeat_time = False
    

    # @api.onchange('contract_parent')
    # def onchange_contract_parent_2(self): 
    #     if self.contract_parent:
    #         join = self.contract_parent
    #         self.claim_type = join.claim_type
    #         self.progressive_milestone_term_id = join.progressive_milestone_term_id
    #         self.repeat_on_month = join.repeat_on_month
    #         self.repeat_day = join.repeat_day
    #         self.repeat_week = join.repeat_week
    #         self.repeat_weekday = join.repeat_weekday
    #         self.repeat_time = join.repeat_time
    #         self.is_create_automatically = join.is_create_automatically

    #         for terms_sale in join.milestone_term_ids:
    #             self.milestone_term_ids = [(0, 0, {
    #                 'name': terms_sale.name,
    #                 'type_milestone': terms_sale.type_milestone,
    #                 'claim_percentage': terms_sale.claim_percentage,
    #             })]

    @api.onchange('claim_type')
    def _onchange_claim_type_change(self):
        for rec in self:
            if rec.claim_type == 'milestone':
                rec.repeat_day = False
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_time = False
                rec.is_create_automatically = False
            elif rec.claim_type == 'monthly':
                rec.milestone_term_ids = False
            else:
                rec.repeat_day = False
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_time = False
                rec.is_create_automatically = False
                rec.milestone_term_ids = False
    
    @api.onchange('repeat_on_month')
    def _onchange_repeat_on_month(self):
        for rec in self:
            if rec.repeat_on_month == 'date':
                rec.repeat_week = False
                rec.repeat_weekday = False
            elif rec.repeat_on_month == 'day':
                rec.repeat_day = False
            else: 
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_day = False

    def create_completion_milestone(self):
        for rec in self:
            if rec.claim_type == 'milestone':
                if rec.milestone_term_ids:

                    stages = []
                    i = 0
                    for milestone in rec.milestone_term_ids:
                        if i == 0:
                            stage_weightage = milestone.claim_percentage
                        else:
                            stage_weightage = milestone.claim_percentage - rec.milestone_term_ids[i-1].claim_percentage

                        stage = rec.env['project.task.type'].create({
                            'name': milestone.name,
                        })
                        stages.append((0, 0, {
                            'name': stage.id,
                            'stage_weightage': stage_weightage,
                        }))
                        i += 1
                    rec.env['project.completion.const'].create({
                        'name': rec.id,
                        'completion_id': rec.project_id.id,
                        'stage_details_ids': stages,
                    })

    def _button_confirm_contd(self):
        res = super(SaleOrderConstInherit, self)._button_confirm_contd()
        for rec in self:
            if rec.claim_type == 'milestone' and not rec.is_set_projects_type and rec.contract_category == 'main':
                rec.create_completion_milestone()
        return res


class SaleMilestoneTerm(models.Model):
    _name = 'sale.milestone.term.const'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Milestone and Terms'
    _order = 'sequence'

    @api.depends('order_id.milestone_term_ids', 'order_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('sale.order.const', string="Order ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type', default="progress")
    claim_percentage = fields.Float(string="Contract Terms (%)")

    @api.onchange('type_milestone')
    def onchange_type(self):
        for res in self:
            if res.type_milestone == 'retention1' or res.type_milestone == 'retention2':
                self.write({'claim_percentage': 100})

class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    is_set_custom_claim = fields.Boolean(string='Set Contract Custom Claims', store=True, related='project.is_set_custom_claim')
    claim_type = fields.Selection([
        ('no_custom', 'No Custom'),
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
        ], string='Based On', default='no_custom', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)],
        'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    progressive_milestone_term_id = fields.Many2one('progressive.milestone.term', string='Milestone and Contract Term Template',readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    milestone_term_ids = fields.One2many('purchase.milestone.term.const', 'order_id', string="Milestone and Term", readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
        ], default='date', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
        'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
        ], readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
        ], readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
        ], readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)], 
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    repeat_time = fields.Selection([
        (str(i), str(i)+'.00') for i in range(0, 24)
        ], string="Time", default=0, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'waiting_for_approval': [('readonly', False)], 'to approve': [('readonly', False)],
                                'rfq_approved': [('readonly', False)], 'request_for_amendment': [('readonly', False)]})
    is_create_automatically = fields.Boolean(string='Create Automatically', default=True)

    def write(self, vals):
        res = super(PurchaseOrderInherit, self).write(vals)
        self.constrains_milestone()
        self._constrains_milestone_type()
        return res
    
    @api.onchange('is_set_custom_claim')
    def _onchange_is_set_custom_claim(self):
        if self.is_subcontracting == True:
            if self.is_set_custom_claim == False:
                # self.claim_type = False
                self.progressive_milestone_term_id = False
                self.milestone_term_ids = False
                self.repeat_day = False
                self.repeat_week = False
                self.repeat_weekday = False
                self.repeat_time = False

    @api.onchange('addendum_payment_method')
    def onchange_vo_payment_type_12(self):
        if self.is_subcontracting == True:
            if self.addendum_payment_method == 'split_payment':
                # self.claim_type = False
                self.progressive_milestone_term_id = False
                self.milestone_term_ids = False
                self.repeat_day = False
                self.repeat_week = False
                self.repeat_weekday = False
                self.repeat_time = False
    
    @api.onchange('contract_parent_po')
    def onchange_contract_parent_2(self): 
        if self.is_subcontracting == True:
            if self.contract_parent_po:
                join = self.contract_parent_po
                self.claim_type = join.claim_type
                self.progressive_milestone_term_id = join.progressive_milestone_term_id
                self.repeat_on_month = join.repeat_on_month
                self.repeat_day = join.repeat_day
                self.repeat_week = join.repeat_week
                self.repeat_weekday = join.repeat_weekday
                self.repeat_time = join.repeat_time
                self.is_create_automatically = join.is_create_automatically

                for terms_sale in join.milestone_term_ids:
                    self.milestone_term_ids = [(0, 0, {
                        'name': terms_sale.name,
                        'type_milestone': terms_sale.type_milestone,
                        'claim_percentage': terms_sale.claim_percentage,
                    })]
    
    @api.onchange('claim_type')
    def _onchange_claim_type_change(self):
        for rec in self:
            if rec.claim_type == 'milestone':
                rec.repeat_day = False
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_time = False
                rec.is_create_automatically = False
            elif rec.claim_type == 'monthly':
                rec.milestone_term_ids = False
            else:
                rec.repeat_day = False
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_time = False
                rec.is_create_automatically = False
                rec.milestone_term_ids = False

    @api.onchange('repeat_on_month')
    def _onchange_repeat_on_month(self):
        for rec in self:
            if rec.repeat_on_month == 'date':
                rec.repeat_week = False
                rec.repeat_weekday = False
            elif rec.repeat_on_month == 'day':
                rec.repeat_day = False
            else: 
                rec.repeat_week = False
                rec.repeat_weekday = False
                rec.repeat_day = False

        
    @api.constrains('milestone_term_ids')
    def constrains_milestone(self):
        for term in self:
            if term.claim_type == 'milestone':
                number_of_lines = len(term.milestone_term_ids)
                if number_of_lines == 0:
                    raise ValidationError(
                        _("You haven't set your milestone, please set it first."))
                for milestone in term.milestone_term_ids:
                    if milestone.type_milestone == "down_payment":
                        if not term.down_payment:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention1":
                        if not term.retention_1:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention2":
                        if not term.retention_2:
                            milestone.unlink()

    @api.constrains('milestone_term_ids')
    def _constrains_milestone_type(self):
        total_progress = 0.0
        progress_flag = False
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                progress_flag = True
                total_progress = line.claim_percentage

        if total_progress < 100.00 and progress_flag:
            raise ValidationError(
                _("Your Progress has a Contract Term less than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))

    
    @api.onchange('milestone_term_ids')
    def _onchange_milestone_type(self):
        last_progress = 0.0
        current_progress = 0.0
        last_progress_name = ""
        current_progress_name = ""
        for line in self.milestone_term_ids:
            if line.type_milestone == 'progress':
                if current_progress >= 100:
                    raise ValidationError(_("Your Progress has been 100%, you can't add more Progress."))
                if line.claim_percentage:
                    last_progress = current_progress
                    last_progress_name = current_progress_name
                    current_progress = line.claim_percentage
                    current_progress_name = line.name
                    if current_progress <= last_progress:
                        raise ValidationError(_("Contract Term of %s can not less than %s, please re-input the Contract Term to bigger than %s%%") % (current_progress_name, last_progress_name, last_progress))
            
        if current_progress > 100.00:
                raise ValidationError(
                    _("Your Progress has a Contract Term more than 100% Please re-input the Contract Term(%) to make sure they add up to 100%."))

        
    @api.onchange('progressive_milestone_term_id')
    def _onchange_progressive_milestone_term_id(self):
        self.milestone_term_ids = [(5, 0, 0)]
        if self.progressive_milestone_term_id:
            miles = self.progressive_milestone_term_id
            for terms in miles.milestone_term_ids:
                milestone_type = terms.type_milestone
                if milestone_type == 'down_payment':
                    if not self.down_payment:
                        continue
                elif milestone_type == 'retention1':
                    if not self.retention_1:
                        continue
                elif milestone_type == 'retention2':
                    if not self.retention_2:
                        continue
                self.milestone_term_ids = [(0, 0, {
                    'name': terms.name,
                    'type_milestone': terms.type_milestone,
                    'claim_percentage': terms.claim_percentage,
                })]

class PurchaseMilestoneTerm(models.Model):
    _name = 'purchase.milestone.term.const'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Milestone and Terms'
    _order = 'sequence'

    @api.depends('order_id.milestone_term_ids', 'order_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.order_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    order_id = fields.Many2one('purchase.order', string="Order ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type', default='progress')
    claim_percentage = fields.Float(string="Contract Terms (%)")

    @api.onchange('type_milestone')
    def onchange_type(self):
        for res in self:
            if res.type_milestone == 'retention1' or res.type_milestone == 'retention2':
                self.write({'claim_percentage': 100})

class ProgressiveClaimInherit(models.Model):
    _inherit = 'progressive.claim'

    is_set_custom_claim = fields.Boolean(string='Set Contract Custom Claim', default=False, store=True)
    claim_type = fields.Selection([
        ('no_custom', 'No Custom'),
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
        ], string='Based On', default='no_custom')
    milestone_term_ids = fields.One2many('account.milestone.term.const', 'claim_id', string="Milestone and Term")
    
    start_month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ])

    start_date_year = fields.Integer('Start Year', store=True, related='contract_parent.start_date_year')
    end_date_year = fields.Integer('End Year', store=True, related='contract_parent.end_date_year')
    start_year = fields.Many2one('const.year', string='Year')

    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
    ], default='date')

    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ])

    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ])

    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ])

    repeat_time = fields.Selection([
        (str(i), str(i)+'.00') for i in range(0, 24)
    ], string="Time")

    is_create_automatically = fields.Boolean(string='Create Automatically', default=False)
    show_claim_revise_button = fields.Binary(default=False, compute='_show_request_revise_buttons')
    count_change = fields.Integer(compute="_compute_count_change")
    change_term_ids = fields.One2many('change.custom.claim', 'claim_id', string="Change History")
    
    def _compute_count_change(self):
        for res in self:
            count = self.env['change.custom.claim'].search_count([('claim_id', '=', res.id)])
            res.count_change = count

    def _show_request_revise_buttons(self):
        for claim in self:
            director = claim.project_id.project_director
            if self.env.user.id == director.id:
                claim.show_claim_revise_button = True
            else:
                claim.show_claim_revise_button = False

    def action_claim_revise(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Change Custom Claim',
                'res_model': 'change.custom.claim.wiz',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                "context": {'default_claim_id': self.id,
                            'default_claim_type': self.claim_type,
                            'default_is_create_automatically': self.is_create_automatically}
                }

    @api.onchange('contract_parent')
    def _onchange_contract_parent_term(self):
        if self.contract_parent:
            res = self.contract_parent
            self.claim_type = res.claim_type
            self.repeat_on_month = res.repeat_on_month
            self.repeat_week = res.repeat_week
            self.repeat_weekday = res.repeat_weekday
            self.repeat_day = res.repeat_day
            self.repeat_time = res.repeat_time
            self.is_create_automatically = res.is_create_automatically
            for mile in res.milestone_term_ids:
                self.milestone_term_ids = [(0, 0, {
                    'name': mile.name,
                    'type_milestone': mile.type_milestone,
                    'claim_percentage': mile.claim_percentage,
                })] 
            if res.is_set_custom_claim == True and res.claim_type != False: 
                self.is_set_custom_claim = True
            else:
                self.is_set_custom_claim = False
    
    @api.onchange('contract_parent_po')
    def _onchange_contract_parent_po_term(self):
        if self.contract_parent_po:
            res = self.contract_parent_po
            self.claim_type = res.claim_type
            self.repeat_on_month = res.repeat_on_month
            self.repeat_week = res.repeat_week
            self.repeat_weekday = res.repeat_weekday
            self.repeat_day = res.repeat_day
            self.repeat_time = res.repeat_time
            self.is_create_automatically = res.is_create_automatically
            for mile in res.milestone_term_ids:
                self.milestone_term_ids = [(0, 0, {
                    'name': mile.name,
                    'type_milestone': mile.type_milestone,
                    'claim_percentage': mile.claim_percentage,
                })]
            if res.is_set_custom_claim == True and res.claim_type != False: 
                self.is_set_custom_claim = True
            else:
                self.is_set_custom_claim = False
    
    # @api.constrains('start_month', 'start_year')
    # def _constraint_start_month(self):
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year:
    #             if rec.start_date and rec.end_date:
    #                 start = rec.start_date
    #                 end = rec.end_date
    #                 start_year = int(start.strftime('%Y'))
    #                 end_year = int(end.strftime('%Y'))
    #                 start_month = int(start.strftime('%m'))
    #                 end_month = int(end.strftime('%m'))
    #                 if start_year == int(rec.start_year.name) and start_month > month_dict[rec.start_month]:
    #                     raise ValidationError(_(f"First claim month can't be before planned start date. Please re-set"))
    #                 elif end_year == int(rec.start_year.name) and end_month < month_dict[rec.start_month]:
    #                     raise ValidationError(_(f"First claim month can't be after planned end date. Please re-set"))
                    
    # @api.constrains('repeat_day', 'repeat_on_month', 'start_month', 'start_year')
    # def _constraint_repeat_day(self):
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year and rec.start_month and rec.repeat_on_month == "date":
    #             start = rec.start_date
    #             end = rec.end_date
    #             start_year = int(start.strftime('%Y'))
    #             end_year = int(end.strftime('%Y'))
    #             start_month = int(start.strftime('%m'))
    #             end_month = int(end.strftime('%m'))
    #             start_day = int(start.strftime('%d'))
    #             end_day = int(end.strftime('%d'))
    #             if start_year == int(rec.start_year.name) and start_month == month_dict[rec.start_month] \
    #                 and int(rec.repeat_day) < start_day:
    #                 raise ValidationError(_(f"First claim date can't be before planned start date. Please re-set"))
    #             elif end_year == int(rec.start_year.name) and end_month == month_dict[rec.start_month] \
    #                 and int(rec.repeat_day) > end_day:
    #                 raise ValidationError(_(f"First claim date can't be after planned end date. Please re-set"))             
    
    # @api.constrains('repeat_weekday', 'repeat_week', 'repeat_on_month', 'start_month', 'start_year')
    # def _constraint_repeat_weekday(self):
    #     week_add_dict = {
    #         "first": 0, "second": 7, "third": 14, "last": 21
    #     }
    #     weekday_dict = {
    #         "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7
    #     }
    #     month_dict = {
    #         "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    #         "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    #     }
    #     for rec in self:
    #         if rec.start_year and rec.start_month and rec.repeat_on_month == "day":
    #             start = rec.start_date
    #             end = rec.end_date
    #             dates = [d for d in Calendar(6).itermonthdates(int(rec.start_year.name), month_dict[rec.start_month])]
    #             date_num = week_add_dict[rec.repeat_week] + weekday_dict[rec.repeat_weekday]
    #             first_claim_date = dates[date_num]
    #             if first_claim_date < start:
    #                 raise ValidationError(_(f"First claim date can't be before planned start date. Please re-set"))
    #             elif first_claim_date > end:
    #                 raise ValidationError(_(f"First claim date can't be after planned end date. Please re-set"))
    
    @api.constrains('milestone_term_ids')
    def constrains_progressive_milestone(self):
        for term in self:
            if term.claim_type == 'milestone':
                for milestone in term.milestone_term_ids:
                    if milestone.type_milestone == "down_payment":
                        if not term.down_payment:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention1":
                        if not term.retention1:
                            milestone.unlink()
                    elif milestone.type_milestone == "retention2":
                        if not term.retention2:
                            milestone.unlink()
    

class AccountMilestoneTerm(models.Model):
    _name = 'account.milestone.term.const'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Milestone and Term'
    _order = 'is_invoiced desc'

    @api.depends('claim_id.milestone_term_ids', 'claim_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.claim_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    claim_id = fields.Many2one('progressive.claim', string="Claim ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type')
    claim_percentage = fields.Float(string="Contract Terms (%)")

    invoice_ids = fields.One2many('account.move', 'milestone_id', string="Invoice") 
    is_invoiced = fields.Boolean(string="Is Invoiced", compute='_compute_is_invoiced', store=True)
    exist_progress_reminder = fields.Boolean(string="Exist Reminder", default=False)

    @api.depends('invoice_ids')
    def _compute_is_invoiced(self):
        for rec in self:
            if len(rec.invoice_ids) > 0:
                rec.is_invoiced = True
            else:
                rec.is_invoiced = False


class ChangeCustomClaim(models.Model):
    _name = 'change.custom.claim'
    _description = 'Change Custom Claim'
    _order = 'id desc'

    @api.depends('claim_id.change_term_ids', 'claim_id.change_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            if len(line.claim_id.change_term_ids)>0:
                no = len(line.claim_id.change_term_ids)
                line.sr_no = no
                i = 0
                for l in line.claim_id.change_term_ids:
                    if i == 0:
                        l.sr_no = no
                        i+=1
                    else:
                        no -= 1
                        l.sr_no = no

    claim_id = fields.Many2one('progressive.claim', string='Claim ID', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer(string="Number of Change", compute="_sequence_ref")
    claim_type = fields.Selection(related="claim_id.claim_type")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    milestone_term_ids = fields.One2many('change.milestone.term.const', 'change_id')
    is_create_automatically = fields.Boolean(string='Create Automatically')
    start_month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ])
    repeat_on_month = fields.Selection([('date', 'Date of the Month'),
                                        ('day', 'Day of the Month')], default='date')
    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ])
    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ])
    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ])
    repeat_time = fields.Selection([
        (str(i), str(i)+'.00') for i in range(0, 24)
    ], string="Time")
    changer = fields.Many2one('res.users', string="Changer")

class ChangeMilestoneTerm(models.Model):
    _name = 'change.milestone.term.const'
    _description = 'Milestone and Term on Change'
    _order = 'sequence'

    @api.depends('change_id.milestone_term_ids', 'change_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.change_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    change_id = fields.Many2one('change.custom.claim', string="Change ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type', default='progress')
    claim_percentage = fields.Float(string="Contract Terms (%)")
    is_invoiced = fields.Boolean(string="Is Invoiced")

class OpportunityDetailsinTerm(models.Model):
    _inherit = 'crm.lead'

    # def _prepare_vals(self, record, list_project, project, short_name, customer, salesperson, team, director):
    #     return {
    #         'name': project,
    #         'project_short_name': short_name,
    #         'project_scope_line_ids': list_project,
    #         'partner_id': customer,
    #         'sales_person' : salesperson,
    #         'sales_team' : team,
    #         'project_director': director,
    #         'department_type': 'project',
    #         'lead_id': record.id,
    #         'notification_claim': [(6, 0, [user.id for user in self.env.user])],
    #     }

    def _prepare_vals(self, record, list_project, project, short_name, customer, salesperson, team, director, branch):
        res = super(OpportunityDetailsinTerm, self)._prepare_vals(record, list_project, project, short_name, customer, salesperson, team, director, branch)
        res['notification_claim'] = [(6, 0, [user.id for user in self.env.user])]

        return res

    
