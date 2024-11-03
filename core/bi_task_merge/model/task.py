# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class Project_Merge(models.TransientModel):
    _name = 'project.task.merge.wizard'


    user_id = fields.Many2one('res.users',string='Assigned To',readonly=True, )
    project_id = fields.Many2one('project.project',string="Project",readonly=True,)
    date_deadline =fields.Date(string="Deadline",readonly=True)
    task_id = fields.Many2one('project.task', string="Merge With", required=True, )

    @api.model
    def default_get(self, fields):
        res = super(Project_Merge, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        current_task_id = self.env['project.task'].browse(active_ids[0])
        if 'user_id' in fields and not res.get('user_id'):
            res ['user_id']= current_task_id.user_id.id
            res['project_id']=current_task_id.project_id.id
            res['date_deadline']=current_task_id.date_deadline

        return res

    def merge_tasks(self):
        desc = ''
        
        tags_id = []
        if self._context.get('active_ids'):
            active_ids = self._context.get('active_ids')
            current_task = self.env['project.task'].browse(active_ids)
            msg_origin = current_task.name + "," + self.task_id.name
        for task in current_task:
            plan_hours = current_task.planned_hours + self.task_id.planned_hours
            for timesheet in current_task.timesheet_ids:
                ts_id=timesheet.copy()
                ts_id.task_id = self.task_id
            tags_id += current_task.tag_ids.ids
            tags_id += self.task_id.tag_ids.ids
            descrip = self.task_id.description
            if descrip:
                desc+= current_task.description
                desc += (self.task_id.description)
            else:
                descrip=''
            for sub_tasks in current_task.child_ids:
                sb_id = sub_tasks.copy()
                sb_id.parent_id = self.task_id
            self.task_id.write({'planned_hours': plan_hours,
                                'date_deadline': self.date_deadline,
                                'project_id': self.project_id.id,
                                'user_id': self.user_id.id,
                                'description': desc,
                                'tag_ids': [(6, 0, tags_id)],
                                })
        msg_body = _("This task  has been created from: <b>%s</b>") % (msg_origin)
        self.task_id.message_post(body=msg_body)


        return True


