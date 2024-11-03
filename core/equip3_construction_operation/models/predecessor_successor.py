from odoo import api, fields, models, _
from datetime import datetime, date , timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT


class ProjectTaskNewInherit(models.Model):
    _inherit = 'project.task'

    duration = fields.Integer(string="Duration", compute='_date_difference', store=True)
    predecessor_ids = fields.One2many('project.task.predecessor', 'task_id')
    successor_ids = fields.One2many('project.task.successor', 'task_id')

    @api.depends('planned_start_date', 'planned_end_date')
    def _date_difference(self):
        for res in self:
            if res.planned_start_date and res.planned_end_date:
                start_date = res.planned_start_date
                end_date = res.planned_end_date
                if end_date >= start_date:
                    res.duration = (end_date - start_date).days
                else:
                    raise ValidationError(_("Start date should not greater than end date."))
            else:
                pass

    # @api.onchange('predecessor_ids')
    # def onchange_predecessor_ids(self):
    #     for res in self:
    #         if res.predecessor_ids:
    #             for work in res.predecessor_ids:
    #                 work.parent_task_id.successor_ids = [(5, 0, 0)]

    #                 if work.parent_task_id:
    #                     work.parent_task_id.successor_ids = [(0, 0, {
    #                         'parent_task_id': work.task_id.id,
    #                         'lag_qty': work.lag_qty if work.lag_qty else 0,
    #                         'type': work.type,
    #                         'lag_type': work.lag_type,
    #                     })]


                
    # def action_inprogress(self):
    #     if self.work_weightage == 0:
    #         raise ValidationError(_("You haven't set job order weightage"))
    #     elif self.is_subcon == True and self.work_subcon_weightage == 0:
    #         raise ValidationError(_("You haven't set job subcon weightage for this subcon"))
    #     elif self.is_subcon == True and self.purchase_subcon == False:
    #         raise ValidationError(_("You haven't set contract subcon for this job order"))
    #     elif self.is_subcon == True and self.purchase_subcon == False and self.work_subcon_weightage == 0:
    #         raise ValidationError(_("You haven't set contract subcon and job subcon weightage for this job order"))
    #     # elif self.is_subtask == False:

    #     elif self.is_subtask == True:
    #         return self.write({'state': 'inprogress', 'purchase_order_exempt' : False})
    #     else:
    #         return self.write({'state': 'inprogress', 'purchase_order_exempt' : False})
    
    # @api.constrains('work_weightage')
    # def onchange_work_weightage_not_null(self):
    #     if self.work_weightage == 0:
    #         raise ValidationError(_("You haven't set job order weightage"))

    # @api.constrains('work_subcon_weightage')
    # def onchange_work_subcon_weightage_not_null(self):
    #     if self.is_subcon == True:
    #         if self.work_subcon_weightage == 0:
    #             raise ValidationError(_("You haven't set job order weightage for this subcon"))
    #     else:
    #         pass


class ProjectTaskPredecessor(models.Model):
    _name = 'project.task.predecessor'
    _description = 'Predecessor'
 
    @api.model
    def _get_link_type(self):
        value = [
            ('FS', _('Finish to Start (FS)')),
            ('SS', _('Start to Start (SS)')),
            ('FF', _('Finish to Finish (FF)')),
            ('SF', _('Start to Finish (SF)')),

        ]
        return value

    task_id = fields.Many2one('project.task', 'Job Order', ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', 'Job Order Predecessor', ondelete='cascade', 
                                      domain="[('project_id','=',parent.project_id), ('sale_order','=', parent.sale_order), ('name','!=', parent.name)]")
    type = fields.Selection('_get_link_type',
                            string='Type',
                            required=True,
                            default='FS')
    project_id = fields.Many2one(related='task_id.project_id', string='Project')
    task_name = fields.Char(related='task_id.name', string='Title')
    sale_order = fields.Many2one(related='task_id.sale_order', string='Contract')
    lag_qty = fields.Integer(string='Lag', default=0)
    lag_type = fields.Selection('_get_lag_type',
                                string='Lag type',
                                required=True,
                                default='day')

    @api.model
    def _get_lag_type(self):
        value = [
            ('minute', _('minute')),
            ('hour', _('hour')),
            ('day', _('day')),
        ]
        return value

    _sql_constraints = [
        ('project_task_link_uniq', 'unique(task_id, parent_task_id, type)', 'Must be unique.'),

    ]

    # def unlink(self):
    #     parent_task_id = self.parent_task_id
    #     res = super(ProjectTaskPredecessor, self).unlink()

    #     if res:
    #         search_if_parent = self.env['project.task.predecessor'].sudo().search_count(
    #             [('parent_task_id', '=', parent_task_id.id)])

    #         if not search_if_parent:
    #             parent_task_id.write({
    #                 'predecessor_parent': 0
    #             })

    #     return res

    @api.model
    def create(self, vals):
        new_id = super(ProjectTaskPredecessor, self).create(vals)
        if new_id.parent_task_id:
            new_id.parent_task_id.successor_ids = [(0, 0, {
                'parent_task_id': new_id.task_id.id,
                'lag_qty': new_id.lag_qty if new_id.lag_qty else 0,
                'type': new_id.type,
                'lag_type': new_id.lag_type,
            })]
        return new_id

    # def unlink(self):
    #     work_id = self.task_id.id
    #     self.unlink()
    #     action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
    #     action['res_id'] = work_id
    #     return action

    
    # def write(self, vals):
    #     old = self.task_id
    #     result = super(ProjectTaskPredecessor, self).write(vals)
    #     if result:
    #         to_del = self.env['project.task.successor'].search([('parent_task_id', '=', old.id)])
    #         if to_del:
    #             to_del[0].unlink()
    #         if self.parent_task_id:
    #             self.parent_task_id.successor_ids = [(0, 0, {
    #                 'parent_task_id': self.task_id.id,
    #                 'lag_qty': self.lag_qty if self.lag_qty else 0,
    #                 'type': self.type,
    #                 'lag_type': self.lag_type,
    #             })]
    #     return result


class ProjectTaskSuccessor(models.Model):
    _name = 'project.task.successor'
    _description = 'Successor'

    task_id = fields.Many2one('project.task', 'Job Order', ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', 'Job Order Successor', 
                     domain="[('project_id','=', parent.project_id), ('sale_order','=', parent.sale_order)]", ondelete='cascade')
    type = fields.Selection('_get_link_type',
                            string='Type',
                            required=True,
                            default='FS')
    project_id = fields.Many2one(related='task_id.project_id', string='Project')
    sale_order = fields.Many2one(related='task_id.sale_order', string='Contract')
    lag_qty = fields.Integer(string='Lag', default=0)
    lag_type = fields.Selection('_get_lag_type',
                                string='Lag type',
                                required=True,
                                default='day')

    @api.model
    def _get_link_type(self):
        value = [
            ('FS', _('Finish to Start (FS)')),
            ('SS', _('Start to Start (SS)')),
            ('FF', _('Finish to Finish (FF)')),
            ('SF', _('Start to Finish (SF)')),

        ]
        return value

    @api.model
    def _get_lag_type(self):
        value = [
            ('minute', _('minute')),
            ('hour', _('hour')),
            ('day', _('day')),
        ]
        return value


