from odoo import api , models, fields, _
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError


class ChangeCustomClaim(models.TransientModel):
    _name = 'change.custom.claim.wiz'
    _description = 'Change Custom Claim Wizard'

    claim_id = fields.Many2one('progressive.claim', string='Claim ID')
    type_change = fields.Selection([
        ('change', 'Change Custom Claim'),
        ('force', 'Force to Create Invoice')
    ], string="Change Type", default='change')

    claim_type = fields.Selection([
        ('no_custom', 'No Custom'),
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
        ], string='Based On')
    milestone_term_ids = fields.One2many('change.milestone.term.const.wiz', 'change_id')
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
    onchange_pass = fields.Boolean(string='Onchange Pass', default=False)

    @api.constrains('milestone_term_ids')
    def _constrains_milestone_type(self):
        total_progress = 0.0
        progress_flag = False
        if self.claim_type == 'milestone':
            for line in self.milestone_term_ids:
                if line.type_milestone == 'progress':
                    progress_flag = True
                    total_progress = max(self.milestone_term_ids.mapped('claim_percentage'))

            if total_progress < 100.00 and progress_flag:
                raise ValidationError(
                    _("Your Progress has a Contract Term less than 100% Please re-input the Contract Term (%) to make sure they add up to 100%."))

    # @api.constrains('milestone_term_ids')
    # def _onchange_milestone_type_constrains(self):
    #     last_progress = 0.0
    #     current_progress = 0.0
    #     last_progress_name = ""
    #     current_progress_name = ""
    #     for line in self.milestone_term_ids:
    #         if line.type_milestone == 'progress':
    #             if line.claim_percentage:
    #                 last_progress = line.claim_percentage[-1]
    #                 last_progress_name = line.name[-1]
    #                 if last_progress:
    #                     current_progress = line.claim_percentage
    #                     current_progress_name = line.name
    #                     if current_progress <= last_progress:
    #                         raise ValidationError(_(f"Contract Term of {current_progress_name} can not less than {last_progress_name}, please re-input the Contract Term to bigger than {last_progress}%"))
    
    
    @api.onchange('milestone_term_ids')
    def _onchange_milestone_type(self):
        if self.onchange_pass:
            if self.claim_type == 'milestone':
                progresses = self.milestone_term_ids.mapped('claim_percentage')
                invoiced_progresses = self.milestone_term_ids.filtered(lambda r: r.is_invoiced == True)
                for line in self.milestone_term_ids:
                    if line.type_milestone == 'progress':
                        if line.claim_percentage:
                            for progress in progresses:
                                progress_count = progresses.count(progress)
                                if progress_count > 1:
                                    raise ValidationError(_("You can't have the same Contract Term (%) for more than one Milestone."))
                            
                            if line.claim_percentage > 100.0:
                                raise ValidationError(_("Your Contract Term (%) can't be greater than 100."))

                            for invoiced in invoiced_progresses:
                                if line.claim_percentage < invoiced.claim_percentage:
                                    raise ValidationError(_("Inputted Contract Term (%) can't be less than the invoiced Contract Term (%)."))
        
        else:
            self.update({'onchange_pass': True})

    @api.onchange('milestone_term_ids')
    def _onchange_milestone_term_ids_validation(self):
        claim = self.env['progressive.claim'].browse([self._context.get('active_id')])
        milestone_current = [line for line in self.milestone_term_ids if line.is_invoiced]
        milestone_origin = [line for line in claim.milestone_term_ids if line.is_invoiced]

        if len(milestone_current) < len(milestone_origin):
            raise ValidationError(_("You can't delete a Milestone that has been invoiced."))

    @api.onchange('claim_id')
    def _onchange_claim_id_term(self):
        if self.claim_id:
            res = self.claim_id
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
                    'reference': mile.id,
                    'type_milestone': mile.type_milestone,
                    'claim_percentage': mile.claim_percentage,
                    'is_invoiced': mile.is_invoiced,
                })]

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

    def is_something_change(self):
        field_to_compare = ['name', 'claim_percentage']
        claim = self.env['progressive.claim'].browse([self._context.get('active_id')])

        change_dict = {}
        for item in self.milestone_term_ids:
            change_dict[item.reference] = item
        
        for item in claim.milestone_term_ids:
            if change_dict.get( item.id, False ):
                for field_name in field_to_compare:
                    if change_dict[item.id][field_name] != item[field_name]:
                        return True
        return False

    def action_confirm(self):
        claim = self.env['progressive.claim'].browse([self._context.get('active_id')])
        change_term_ids = self.env['change.custom.claim'].search([('claim_id', '=', claim.id)])

        if self.claim_type == 'monthly':
            if self.repeat_on_month == 'date':
                if claim.repeat_on_month == self.repeat_on_month and claim.repeat_day == self.repeat_day and claim.repeat_time == self.repeat_time and claim.is_create_automatically == self.is_create_automatically:
                    raise ValidationError(_("You didn't make any change."))
            elif self.repeat_on_month == 'day':
                if claim.repeat_on_month == self.repeat_on_month and claim.repeat_week == self.repeat_week and claim.repeat_weekday == self.repeat_weekday and claim.repeat_time == self.repeat_time and claim.is_create_automatically == self.is_create_automatically:
                    raise ValidationError(_("You didn't make any change."))
            
            if len(change_term_ids) == 0:
                change_term_ids.create({
                    'claim_id': claim.id,
                    'start_date': claim.create_date,
                    'end_date': datetime.today(),
                    'changer':  self.env.user.id,
                    'repeat_on_month': claim.repeat_on_month,
                    'repeat_week': claim.repeat_week,
                    'repeat_weekday': claim.repeat_weekday,
                    'repeat_day': claim.repeat_day,
                    'repeat_time': claim.repeat_time,
                    'is_create_automatically': claim.is_create_automatically,
                })
            
            
            elif len(change_term_ids)>0:
                last = len(change_term_ids)
                change_history = self.env['change.custom.claim'].search([('claim_id', '=', claim.id),('sr_no', '=', last)],limit=1)
                # last_date = change_term_ids[-1].end_date
                change_term_ids.create({
                    'claim_id': claim.id,
                    'start_date': change_history.end_date,
                    'end_date': datetime.today(),
                    'changer': self.env.user.id,
                    'repeat_on_month': claim.repeat_on_month,
                    'repeat_week': claim.repeat_week,
                    'repeat_weekday': claim.repeat_weekday,
                    'repeat_day': claim.repeat_day,
                    'repeat_time': claim.repeat_time,
                    'is_create_automatically': claim.is_create_automatically,
                })
                    
            claim.write({'repeat_on_month': self.repeat_on_month,
                         'repeat_week': self.repeat_week,
                         'repeat_weekday': self.repeat_weekday,
                         'repeat_day': self.repeat_day,
                         'repeat_time': self.repeat_time,
                         'is_create_automatically': self.is_create_automatically,
                       })

        else:
            if not self.is_something_change():
                raise ValidationError(_("You didn't make any change."))
            
            def _create_history():
                if len(change_term_ids) == 0:
                    change_history = change_term_ids.create({
                        'claim_id': claim.id,
                        'start_date': claim.create_date,
                        'end_date': datetime.today(),
                        'changer': self.env.user.id,
                    })
                    milestone_values = []
                    for milestone in claim.milestone_term_ids:
                        milestone_values.append((0, 0,{
                            'name': milestone.name,
                            'type_milestone': milestone.type_milestone,
                            'claim_percentage': milestone.claim_percentage,
                            'is_invoiced': milestone.is_invoiced,
                        }))
                    change_history.milestone_term_ids = milestone_values

                    claim.milestone_term_ids = [(5,0,0)]
                    milestone_term_values = []
                    for milestone in self.milestone_term_ids:
                        milestone_term_values.append((0, 0,{
                            'name': milestone.name,
                            'type_milestone': milestone.type_milestone,
                            'claim_percentage': milestone.claim_percentage,
                            'is_invoiced': milestone.is_invoiced,
                        }))
                    claim.milestone_term_ids = milestone_term_values


                elif len(change_term_ids)>0:
                    last = len(change_term_ids)
                    change_new = self.env['change.custom.claim'].search([('claim_id', '=', claim.id),('sr_no', '=', last)],limit=1)
                    # last_date = change_term_ids[-1].end_date
                    change_history = change_term_ids.create({
                        'claim_id': claim.id,
                        'start_date': change_new.end_date,
                        'end_date': datetime.today(),
                        'changer': self.env.user.id,
                    })
                    milestone_values = []
                    for milestone in claim.milestone_term_ids:
                        milestone_values.append((0, 0, {
                            'name': milestone.name,
                            'type_milestone': milestone.type_milestone,
                            'claim_percentage': milestone.claim_percentage,
                            'is_invoiced': milestone.is_invoiced,
                        }))
                    change_history.milestone_term_ids = milestone_values


                    claim.milestone_term_ids = [(5,0,0)]
                    milestone_term_values = []
                    for milestone in self.milestone_term_ids:
                        milestone_term_values.append((0, 0,{
                            'name': milestone.name,
                            'type_milestone': milestone.type_milestone,
                            'claim_percentage': milestone.claim_percentage,
                            'is_invoiced': milestone.is_invoiced,
                        }))
                    claim.milestone_term_ids = milestone_term_values
            
            if len(self.milestone_term_ids) != len(claim.milestone_term_ids):
                for line in self.milestone_term_ids:
                    if line.claim_percentage == 100 and line != self.milestone_term_ids[-1]:
                        raise ValidationError(_("You can't add milestone below 100%."))
                    else:
                        _create_history()
            
            elif self.milestone_term_ids != claim.milestone_term_ids:
                for line in self.milestone_term_ids:
                    if line.claim_percentage == 100 and line != self.milestone_term_ids[-1]:
                        raise ValidationError(_("You can't add milestone below 100%."))
                    else:
                        _create_history()
            else:
                raise ValidationError(_("You didn't make any change."))          

            
            # for line in self.milestone_term_ids:
            #     if not line.is_invoiced:
            #         claim.milestone_term_ids = [(0, 0, {
            #             'name': line.name,
            #             'type_milestone': line.type_milestone,
            #             'claim_percentage': line.claim_percentage,
            #             'is_invoiced': line.is_invoiced,
            #         })]
            # i = 0
            # for milestone in claim.milestone_term_ids:
            #     if i < len(self.milestone_term_ids.filtered(lambda x: x.is_invoiced == False).sorted(key=lambda x: x.claim_percentage)):
            #         if not milestone.is_invoiced:
            #             milestone.unlink()
            #             i += 1
            #     else:
            #         break

            # for line in self.milestone_term_ids:
            #     if not line.is_invoiced:
            #         claim.milestone_term_ids = [(0, 0, {
            #             'name': line.name,
            #             'type_milestone': line.type_milestone,
            #             'claim_percentage': line.claim_percentage,
            #             'is_invoiced': line.is_invoiced,
            #         })]

        
    def create_invoice(self):
        claim = self.env['progressive.claim'].browse([self._context.get('active_id')])
        if self.claim_type == 'monthly':
            if self.is_create_automatically:
                claim_request = self.env['claim.request'].create({'request_for': 'progress',
                           'progressive_bill': claim.progressive_bill,
                           'project_id': claim.project_id.id or False,
                           'partner_id': claim.partner_id.id or False,
                           'vendor': claim.vendor.id or False,
                           'branch_id': claim.branch_id.id or False,
                           'project_director': claim.project_director.id or False,
                           'contract_amount': claim.contract_amount,
                           'down_payment': claim.down_payment,
                           'dp_amount': claim.dp_amount,
                           'retention1': claim.retention1,
                           'retention2': claim.retention2,
                           'retention1_amount': claim.retention1_amount,
                           'retention2_amount': claim.retention2_amount,
                           'last_progress': claim.approved_progress,
                           'progressive_claim_id': claim.id,
                           'contract_parent': claim.contract_parent.id or False,
                           'contract_parent_po': claim.contract_parent_po.id or False,
                           })

                work_order_invoice = None
                work_order_subcon = None

                if claim.progressive_bill == False:
                    had_claim_request = self.env['claim.request.line'].search([('state', '!=', 'to_approve')]).mapped('request_id')
                    domain_3 = [('request_id', 'in', had_claim_request.ids), ('project_id', '=', claim.project_id.id)]
                    project_task_ids = self.env['const.request.line'].search(domain_3).mapped('work_order')
                    ids = []

                    for task in project_task_ids:
                        if task.progress_task <= task.last_progress:
                            ids.append(task.id)

                    work_order_invoice = self.env['project.task'].search(
                        [('project_id', '=', claim.project_id.id), ('sale_order', '=', claim.contract_parent.id),
                         ('state', '!=', 'draft'), ('claim_request', '=', True),
                         ('is_greater_current_progress', '=', True), ('is_subtask', '=', False), ('id', 'not in', ids)])

                    if len(work_order_invoice)>0:
                        for task in work_order_invoice:
                            claim_request.request_line_ids = [(0, 0, {
                                'work_order': task.id or False,
                                'stage_new': task.stage_new and task.stage_new.id or False,
                                'assigned_to': task.assigned_to and task.assigned_to.id or False,
                                'completion_date': task.actual_end_date,
                                'stage_weightage': task.stage_weightage,
                                'work_progress': task.progress_task,
                                'work_weightage': task.work_weightage,
                                'last_progress': task.last_progress,
                                'wo_prog_temp': task.wo_prog_temp,
                                'progressive_bill' : claim.progressive_bill
                        })]

                    claim_request.onchange_request_line_ids()
                    claim_request._temp_amount_calculation()
                    claim_request._max_claim_calculation()
                    claim_request._remaining_request_calculation()

                    claim_request._compute_account_1()
                    claim_request._compute_account_2()
                    claim_request._compute_account_3()
                    claim_request._compute_account_4()

                    claim_request.send_request()
                    claim_request_line = self.env['claim.request.line'].search([('request_id', '=', claim_request.id)])
                    claim_request_line.action_confirm_approving()
                    claim_request_line.write({
                        'state': 'approved',
                        'approved_progress' : claim_request_line.requested_progress
                    })
                    const = self.env['project.claim'].search(
                        [('claim_id', '=', claim.id), ('claim_for', '=', 'progress'),
                         ('progressline', '=', claim.invoiced_progress)], limit=1)
                    tot = sum(const.mapped('gross_amount'))

                    progressive_invoice_wizard = self.env['progressive.invoice.wiz'].create({
                               'invoice_for': 'progress',
                               'progressive_bill': claim.progressive_bill,
                               'approved_progress': claim.approved_progress,
                               'contract_amount': claim.contract_amount,
                               'last_progress': claim.invoiced_progress,
                               'last_amount': tot,
                               'down_payment': claim.down_payment,
                               'dp_amount': claim.dp_amount,
                               'retention1': claim.retention1,
                               'retention2': claim.retention2,
                               'retention1_amount': claim.retention1_amount,
                               'retention2_amount': claim.retention2_amount,
                               'tax_id': [(6, 0, [v.id for v in claim.tax_id])],
                               'progressive_claim_id': claim.id,
                               })

                    progressive_invoice_wizard._compute_approved_amount()
                    progressive_invoice_wizard._compute_last_amount()
                    progressive_invoice_wizard.onchange_method()
                    progressive_invoice_wizard._compute_amount()
                    progressive_invoice_wizard.create_invoice()

                else:
                    # pass
                    had_claim_request = self.env['claim.request.line'].search(
                        [('state', '!=', 'to_approve')]).mapped('request_id')
                    domain_4 = [('request_id', 'in', had_claim_request.ids), ('project_id', '=', self.project_id.id)]
                    project_task_ids = self.env['const.request.line'].search(domain_4).mapped('work_order_sub')
                    ids = []
                    for task in project_task_ids:
                        if task.progress_task <= task.last_progress:
                            ids.append(task.id)
                    # work_order_subcon += [('id', 'not in', ids)]
                    work_order_subcon = self.env['project.task'].search(
                        [('project_id', '=', self.project_id.id),
                        ('purchase_subcon', '=',self.contract_parent_po.id),
                        ('state', '!=', 'draft'),
                        ('claim_request', '=', True),
                        ('is_subcon', '=', True),
                        ('is_greater_current_progress', '=', True),
                        ('is_subtask', '=', False),('id', 'not in', ids)])

                    if len(work_order_subcon)>0:
                        for task in work_order_subcon:
                            claim_request.request_line_ids = [(0, 0, {
                                'work_order': task.id or False,
                                'stage_new': task.stage_new and task.stage_new.id or False,
                                'assigned_to': task.assigned_to and task.assigned_to.id or False,
                                'completion_date': task.actual_end_date,
                                'stage_weightage': task.stage_weightage,
                                'work_progress': task.progress_task,
                                'work_weightage': task.work_weightage,
                                'last_progress': task.last_progress,
                                'wo_prog_temp': task.wo_prog_temp,
                                'progressive_bill' : claim.progressive_bill
                        })]

                    claim_request.onchange_request_line_ids()
                    claim_request._temp_amount_calculation()
                    claim_request._max_claim_calculation()
                    claim_request._remaining_request_calculation()

                    claim_request._compute_account_1()
                    claim_request._compute_account_2()
                    claim_request._compute_account_3()
                    claim_request._compute_account_4()

                    claim_request.send_request()
                    claim_request_line = self.env['claim.request.line'].search([('request_id', '=', claim_request.id)])
                    claim_request_line.action_confirm_approving()
                    claim_request_line.write({
                        'state': 'approved',
                        'approved_progress' : claim_request_line.requested_progress
                    })
                    const = self.env['project.claim'].search(
                        [('claim_id', '=', claim.id), ('claim_for', '=', 'progress'),
                         ('progressline', '=', claim.invoiced_progress)], limit=1)
                    tot = sum(const.mapped('gross_amount'))

                    progressive_invoice_wizard = self.env['progressive.invoice.wiz'].create({
                               'invoice_for': 'progress',
                               'progressive_bill': claim.progressive_bill,
                               'approved_progress': claim.approved_progress,
                               'contract_amount': claim.contract_amount,
                               'last_progress': claim.invoiced_progress,
                               'last_amount': tot,
                               'down_payment': claim.down_payment,
                               'dp_amount': claim.dp_amount,
                               'retention1': claim.retention1,
                               'retention2': claim.retention2,
                               'retention1_amount': claim.retention1_amount,
                               'retention2_amount': claim.retention2_amount,
                               'tax_id': [(6, 0, [v.id for v in claim.tax_id])],
                               'progressive_claim_id': claim.id,
                               })

                    progressive_invoice_wizard._compute_approved_amount()
                    progressive_invoice_wizard._compute_last_amount()
                    progressive_invoice_wizard.onchange_method()
                    progressive_invoice_wizard._compute_amount()
                    progressive_invoice_wizard.create_invoice()

            else:
                claim_history = claim.claim_ids.filtered(lambda x: x.claim_for == 'down_payment')
                if claim_history:
                    if claim.dp_able:
                        raise ValidationError(_('Complete the down payment invoice creation first.'))
                else:
                    if claim.dp_able:
                        raise ValidationError(_('Complete the down payment invoice creation first.'))

                if claim.approved_progress == claim.invoiced_progress:
                    if claim.progressive_bill:
                        raise ValidationError(_('There is no progress to be billed.'))
                    else:
                        raise ValidationError(_('There is no progress to be invoiced.'))

                context = {'force_create_invoice_progress': True}
                if claim.progressive_bill:
                    return claim.with_context(context).create_bill_progress()
                else:
                    return claim.with_context(context).create_invoice_progress()

        else:
            claim_history = claim.claim_ids.filtered(lambda x: x.claim_for == 'down_payment')
            if claim_history:
                if claim.dp_able:
                    raise ValidationError(_('Complete the down payment invoice creation first.'))
            else:
                if claim.dp_able:
                    raise ValidationError(_('Complete the down payment invoice creation first.'))

            if claim.approved_progress == claim.invoiced_progress:
                if claim.progressive_bill:
                    raise ValidationError(_('There is no progress to be billed.'))
                else:
                    raise ValidationError(_('There is no progress to be invoiced.'))

            context = {'force_create_invoice_progress': True}
            if claim.progressive_bill:
                return claim.with_context(context).create_bill_progress()
            else:
                return claim.with_context(context).create_invoice_progress()


class ChangeMilestoneTerm(models.TransientModel):
    _name = 'change.milestone.term.const.wiz'
    _description = 'Milestone and Term on Change Wizard'
    _order = 'sequence'

    @api.depends('change_id.milestone_term_ids', 'change_id.milestone_term_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.change_id.milestone_term_ids:
                no += 1
                l.sr_no = no

    change_id = fields.Many2one('change.custom.claim.wiz', string="Change ID", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    reference = fields.Integer(string="Reference from Milestone and Term on Change", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    name = fields.Char(string='Milestone Name')
    type_milestone = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Milestone Type', default='progress')
    claim_percentage = fields.Float(string="Contract Terms (%)")
    is_invoiced = fields.Boolean(string="Invoiced")


        
        
