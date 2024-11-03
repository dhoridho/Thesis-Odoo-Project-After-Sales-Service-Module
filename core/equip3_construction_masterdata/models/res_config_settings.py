from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_subtask_project = fields.Boolean("Sub-tasks", default=True, implied_group="project.group_subtask_project")
    
    @api.constrains('cons_use_code')
    def _compute_complete_name_scope(self):
        for res in self:
            scope = self.env['project.scope.line'].search([])
            if res.cons_use_code == True:
                if scope:
                    for rec in scope:
                        if rec.code and rec.name:
                            rec.complete_name = '%s - %s' % (rec.code, rec.name)
                        elif not rec.code and rec.name:
                            rec.complete_name = '%s' % (rec.name)
                        else:
                            pass
                else:
                    pass
            else:
                if scope:
                    for rec in scope:
                        if rec.name:
                            rec.complete_name = '%s' % (rec.name)
                        else:
                            pass
                else:
                    pass

            section = self.env['section.line'].search([])
            if res.cons_use_code == True:
                if section:
                    for rec in section:
                        if rec.code and rec.name:
                            rec.complete_name = '%s - %s' % (rec.code, rec.name)
                        elif not rec.code and rec.name:
                            rec.complete_name = '%s' % (rec.name)
                        else:
                            pass
                else:
                    pass
            else:
                if section:
                    for rec in section:
                        if rec.name:
                            rec.complete_name = '%s' % (rec.name)
                        else:
                            pass
                else:
                    pass
