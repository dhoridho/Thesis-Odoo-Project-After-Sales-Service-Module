from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date, timedelta


class ProjectTaskCompletionWizard(models.TransientModel):
    """Project task completion validation will be handled here"""
    _inherit = 'project.task.completion.wizard'

    def confirm(self):
        res = super(ProjectTaskCompletionWizard, self).confirm()
        for record in self:
            if record.project_task_id.state == 'complete':
                # remove corresponding employee active location from project information line
                self.env.cr.execute("DELETE FROM construction_project_information WHERE project_task_id = %s", (record.project_task_id.id,))
                active_locations = tuple(self.project_task_id.active_location_ids.active_location_id.ids)
                if len(active_locations) > 0:
                    for worker in self.project_task_id.employee_worker_ids:
                        # active_location_id in active_locations
                        self.env.cr.execute(
                            "DELETE FROM active_location WHERE employee_id = %s AND active_location_id IN %s",
                            (worker.id, active_locations))
                        if len(worker.active_location_ids) > 0:
                            worker.active_location_ids[0].write({'is_default': True})
        return res
