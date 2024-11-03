from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError


class CompletionIssueWizard(models.TransientModel):
    '''All project task completion issue related to predecessor and successor will be handled in this wizard'''
    _inherit = 'completion.issue.wizard'
    _description = 'Project Task Completion Issues'

    def force_complete(self, task):
        res = super(CompletionIssueWizard, self).force_complete(task)
        if task.state == 'complete':
            # remove corresponding employee active location from project information line
            self.env.cr.execute("DELETE FROM construction_project_information WHERE project_task_id = %s", (task.id,))
            active_locations = tuple(task.active_location_ids.active_location_id.ids)
            if len(active_locations) > 0:
                for worker in task.employee_worker_ids:
                    # active_location_id in active_locations
                    self.env.cr.execute("DELETE FROM active_location WHERE employee_id = %s AND active_location_id IN %s", (worker.id, active_locations))
                    if len(worker.active_location_ids) > 0:
                        worker.active_location_ids[0].write({'is_default': True})
        return res

    def force_confirm(self, task):
        res = super(CompletionIssueWizard, self).force_confirm(task)
        if len(res) > 0 and type(res) is not dict:
            # check if employee is in multiple usage
            already_assigned_employee = []

            for usage in res:
                for worker in usage.workers_ids:
                    if worker.id in already_assigned_employee:
                        raise ValidationError(
                            _("Employee %s have multiple position in one active location. Please adjust it again.") % worker.name)
                    for location in usage.project_task_id.active_location_ids:
                        if location._origin.id in worker.project_information_ids.active_location_id.ids:
                            raise ValidationError(_("Employee %s is already assigned to location %s") % (worker.name, location.name))
                        self.env.cr.execute(
                            "SELECT id,rate_amount FROM labour_cost_rate WHERE project_id = %s AND group_of_product_id = %s AND product_id = %s AND active_location_id = %s",
                            (usage.project_task_id.project_id.id, usage.group_of_product_id.id, usage.product_id.id,
                             location.id))
                        if self.env.cr.rowcount > 0:
                            labour_cost_rate = self.env.cr.fetchone()
                        else:
                            labour_cost_rate = False
                        if labour_cost_rate:
                            worker.project_information_ids.create({
                                'project_id': usage.project_task_id.project_id.id,
                                'project_task_id': usage.project_task_id.id,
                                'active_location_id': location.id,
                                'project_scope_id': usage.project_scope_id.id,
                                'section_id': usage.section_id.id,
                                'group_of_product_id': usage.group_of_product_id.id,
                                'product_id': usage.product_id.id,
                                'employee_id': worker.id,
                                # 'uom_id': labour_cost_rate[1],
                                'rate_amount': labour_cost_rate[1],
                                'labour_cost_rate_id': labour_cost_rate[0],
                            })
                            worker.active_location_ids.create({
                                'employee_id': worker.id,
                                'active_location_id': location.active_location_id.id,
                                'is_default': True if len(worker.active_location_ids) == 0 else False,
                            })
                        else:
                            worker.project_information_ids.create({
                                'project_id': usage.project_task_id.project_id.id,
                                'project_task_id': usage.project_task_id.id,
                                'active_location_id': location.id,
                                'project_scope_id': usage.project_scope_id.id,
                                'section_id': usage.section_id.id,
                                'group_of_product_id': usage.group_of_product_id.id,
                                'product_id': usage.product_id.id,
                                'employee_id': worker.id,
                            })
                            worker.active_location_ids.create({
                                'employee_id': worker.id,
                                'active_location_id': location.active_location_id.id,
                                'is_default': True if len(worker.active_location_ids) == 0 else False,
                            })

                        already_assigned_employee.append(worker.id)
        return res