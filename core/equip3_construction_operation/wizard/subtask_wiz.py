from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class CreateSubtaskWiz(models.TransientModel):
    _name = 'create.subtask.wiz'
    _description = 'Create Subtasks'

    def create_subtask(self):
        parent_task = self.parent_task
        if not parent_task:
            parent_task = self.env['project.task'].browse(self.env.context.get('active_id'))

        if not self.subtasks_ids:
            raise ValidationError(_("Add at least one subtask to create."))

        flag = True
        # Check Validation
        for line in self.subtasks_ids:
            if parent_task.state == 'inprogress':
                if line.planned_start_date <= parent_task.actual_start_date:
                    raise ValidationError(_("Planned start date should not be less than parent task's actual start date."))
                if line.planned_start_date > line.planned_end_date:
                    raise ValidationError(_("Planned start date should not exceed planned end date."))
                if not (line.planned_start_date >= parent_task.planned_start_date and line.planned_start_date <= parent_task.planned_end_date) or \
                        (line.planned_end_date <= parent_task.planned_start_date and line.planned_end_date <= parent_task.planned_end_date):
                    flag = False
                    raise ValidationError(_("You must input the start date or end date in between the start and end date of "+str(parent_task.name)+"'s task."))
            else:
                if line.planned_start_date > line.planned_end_date:
                    raise ValidationError(_("Planned start date should not exceed planned end date."))
                if not (line.planned_start_date >= parent_task.planned_start_date and line.planned_start_date <= parent_task.planned_end_date) or \
                        (line.planned_end_date <= parent_task.planned_start_date and line.planned_end_date <= parent_task.planned_end_date):
                    flag = False
                    raise ValidationError(_("You must input the start date or end date in between the start and end date of "+str(parent_task.name)+"'s task."))
        
        # validate subtask's name
        subtask_names = []
        parents = self.env['project.task'].search([
            ('project_id', '=', parent_task.project_id.id),
            ('sale_order', '=', parent_task.sale_order.id),
            ('stage_new', '=', parent_task.stage_new.id)
            ])
        for p in parents:
            for s in p.subtask_ids:
                subtask_names.append(s.name)
        for sub in self.subtasks_ids:
            if sub.name in subtask_names:
                raise ValidationError(_("The name of the subtask of parent tasks with the same contract's stage must be unique."))
            subtask_names.append(sub.name)

        # validate subtask weightage
        for sub in self.subtasks_ids:
            if sub.work_subtask_weightage <= 0:
                raise ValidationError(_("Subtask weightage must be greater than 0%."))
        
        if flag:
            for sub in self.subtasks_ids:
                if parent_task.is_subtask == False:
                    vals = {
                        'project_id': parent_task.project_id.id,
                        'partner_id': parent_task.partner_id.id,
                        'sale_order': parent_task.sale_order.id,
                        'completion_ref': parent_task.completion_ref.id,
                        'stage_new': parent_task.stage_new.id,
                        'project_director': parent_task.project_director.id,
                        'cost_sheet': parent_task.cost_sheet.id,
                        'branch_id': parent_task.branch_id.id,
                        'name': sub.name,
                        'new_description': sub.description,
                        'assigned_to': sub.assigned_to.id,
                        'is_subtask': True,
                        'is_subcon': parent_task.is_subcon,
                        'planned_hours': sub.planned_hour,
                        'assigned_date': sub.assigned_date,
                        'planned_start_date': sub.planned_start_date,
                        'planned_end_date': sub.planned_end_date,
                        'purchase_subcon': parent_task.purchase_subcon.id,
                        'work_subcon_weightage': parent_task.work_subcon_weightage,
                        'sub_contractor': parent_task.sub_contractor.id,
                        'stage_weightage': parent_task.stage_weightage,
                        'work_weightage': parent_task.work_weightage,
                        'work_subtask_weightage': sub.work_subtask_weightage,
                        'active_location_ids': [(6, 0, parent_task.active_location_ids.ids)]
                    }
                else:
                    vals = {
                        'project_id': parent_task.project_id.id,
                        'partner_id': parent_task.partner_id.id,
                        'sale_order': parent_task.sale_order.id,
                        'completion_ref': parent_task.completion_ref.id,
                        'stage_new': parent_task.stage_new.id,
                        'project_director': parent_task.project_director.id,
                        'cost_sheet': parent_task.cost_sheet.id,
                        'branch_id': parent_task.branch_id.id,
                        'name': sub.name,
                        'new_description': sub.description,
                        'assigned_to': sub.assigned_to.id,
                        'is_subtask': True,
                        'is_subcon': parent_task.is_subcon,
                        'planned_hours': sub.planned_hour,
                        'assigned_date': sub.assigned_date,
                        'planned_start_date': sub.planned_start_date,
                        'planned_end_date': sub.planned_end_date,
                        'purchase_subcon': parent_task.purchase_subcon.id,
                        'work_subcon_weightage': parent_task.work_subcon_weightage,
                        'sub_contractor': parent_task.sub_contractor.id,
                        'stage_weightage': parent_task.stage_weightage,
                        'work_weightage': parent_task.work_subtask_weightage,
                        'work_subtask_weightage': sub.work_subtask_weightage,
                        'active_location_ids': [(6, 0, parent_task.active_location_ids.ids)]
                    }

                task = self.env['project.task'].create(vals)
                
                # list_subtask = []
                # list_subtask.append(
                #     (0, 0, {'subtask_id': parent_task and parent_task.id or False,
                #             'name': sub.name,
                #             'description': sub.description,
                #             'assigned_to': sub.assigned_to and sub.assigned_to.id or False,
                #             'assigned_date': sub.assigned_date,
                #             'planned_hour': sub.planned_hour,
                #             'work_subtask_weightage': sub.work_subtask_weightage
                #             }
                #     ))
            # self.parent_task.write({
            #     'subtask_ids': list_subtask,
            # })
                self.parent_task.write({
                    'related_subtask_ids':  [(4, task.id)]
                })

        return True

    txt = fields.Text(string="Information", default="This wizard will create subtasks of current job order.")
    subtasks_ids = fields.One2many('create.subtask', 'subtask_id')
    parent_task = fields.Many2one('project.task', string="Parent Task")
    subtask_planned_hours = fields.Float(string="Subtask Planned Hours", compute="compute_planned_hour")

    @api.depends('subtasks_ids.planned_hour')
    def compute_planned_hour(self):
        hours = 0
        for res in self:
            hours = sum(res.subtasks_ids.mapped('planned_hour'))
            res.subtask_planned_hours = hours
        return hours

    @api.onchange('subtask_planned_hours')
    def _compute_subtask_planned_hours(self):
        for res in self:
            if res.subtask_planned_hours > res.parent_task.planned_hours:
                raise ValidationError(_('The number of subtask planned hours exceeds the planned hours of the parent task.\nPlease re-set the planned hours of subtasks.'))
            else:
                pass
    
    # @api.onchange('subtasks_ids')
    # def compute_work_subtask_weightage(self):
    #     weightage = 0
    #     for res in self:
    #         if res.subtasks_ids:
    #             weightage = sum(res.subtasks_ids.mapped('work_subtask_weightage'))
    #             for rec in self.env['project.task'].search([('is_subtask','=',True),('project_id', '=', res.project_id.id), ('sale_order', '=', res.sale_order.id), ('parent_task', '=', res.parent_task.id)]):
    #                 total += rec.work_subtask_weightage
    #             total_subtask = total + weightage
    #             if total_subtask > 100:
    #                 raise ValidationError(_('Total Weightage of all subtask in parent task is more than 100%.\nPlease re-set the weightage of subtasks.'))
    #     return weightage

    @api.onchange('subtasks_ids')
    def _onchange_work_subtask_weightage(self):
        parent_task = self.parent_task
        progress = parent_task.progress_task
        if parent_task:
            subtask_weightage_sum = 0
            for sub in parent_task.related_subtask_ids:
                subtask_weightage_sum += sub.work_subtask_weightage

            for res in self.subtasks_ids:
                if res.work_subtask_weightage:
                    subtask_weightage_sum += res.work_subtask_weightage
            
            rest_weig = 100 - progress
            
            final_weightage = progress + subtask_weightage_sum 
            if final_weightage > 100:
                raise ValidationError(_("Total weightage of all subtask and progress in parent task cannot be more than 100%.\nPlease re-set the weightage of subtasks. (Remaining weightage for all subtasks = '{}%')".format(rest_weig)))
    
    
class SubtaskWiz(models.TransientModel):
    _name = 'create.subtask'
    _description = 'Create Subtasks'

    subtask_id = fields.Many2one('create.subtask.wiz', string='Subtask')
    name = fields.Char(string="Subtask")
    description = fields.Text(string="Subtask Description")
    assigned_to = fields.Many2one('res.users', string="PIC")
    assigned_date = fields.Datetime(string="Assigned Date", default=fields.Datetime.now)
    planned_hour = fields.Float(string="Planned Hours")
    planned_start_date = fields.Datetime(string="Planned Start Date")
    planned_end_date = fields.Datetime(string="Planned End Date")
    work_subtask_weightage = fields.Float(string="Subtask Weightage")
