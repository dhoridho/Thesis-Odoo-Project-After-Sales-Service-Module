# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_planned_table = fields.Integer(
        'Planned Activities Table Limit', default=10)
    sh_all_table = fields.Integer('All Activities Table Limit', default=10)
    sh_completed_table = fields.Integer(
        'Completed Activities Table Limit', default=10)
    sh_due_table = fields.Integer('Due Activities Table Limit', default=10)
    sh_cancel_table = fields.Integer('Cancelled Activities Table Limit', default=10)
    sh_display_multi_user = fields.Boolean('Display Multi Users ?')
    sh_display_all_activities_counter = fields.Boolean('All Activities Counter',default=True)
    sh_display_planned_activities_counter = fields.Boolean('Planned Activities Counter',default=True)
    sh_display_completed_activities_counter = fields.Boolean('Completed Activities Counter',default=True)
    sh_display_overdue_activities_counter = fields.Boolean('Overdue Activities Counter',default=True)
    sh_display_cancelled_activities_counter = fields.Boolean('Cancelled Activities Counter',default=True)
    sh_display_all_activities_table = fields.Boolean('All Activities Table Counter',default=True)
    sh_display_planned_activities_table = fields.Boolean('Planned Activities Table',default=True)
    sh_display_completed_activities_table = fields.Boolean('Completed Activities Table',default=True)
    sh_display_overdue_activities_table = fields.Boolean('Overdue Activities Table',default=True)
    sh_display_cancelled_activities_table = fields.Boolean('Cancelled Activities Table',default=True)
    sh_display_activity_reminder = fields.Boolean('Activity Reminder ?',default=True)
    sh_document_model = fields.Boolean('Display document model wise activity ?')
    sh_document_model_ids = fields.Many2many('ir.model','sh_ir_model_res_company_rel', 'sh_company_id', 'sh_model_id',string='Document Models')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_planned_table = fields.Integer(
        'Planned Activities Table Limit', related='company_id.sh_planned_table',readonly=False)
    sh_all_table = fields.Integer(
        'All Activities Table Limit', related='company_id.sh_all_table',readonly=False)
    sh_completed_table = fields.Integer(
        'Completed Activities Table Limit', related='company_id.sh_completed_table',readonly=False)
    sh_due_table = fields.Integer(
        'Due Activities Table Limit', related='company_id.sh_due_table',readonly=False)
    sh_cancel_table = fields.Integer('Cancelled Activities Table Limit', related='company_id.sh_cancel_table',readonly=False)
    sh_display_multi_user = fields.Boolean('Display Multi Users ?',related='company_id.sh_display_multi_user',readonly=False)
    sh_display_all_activities_counter = fields.Boolean('All Activities Counter',related='company_id.sh_display_all_activities_counter',readonly=False)
    sh_display_planned_activities_counter = fields.Boolean('Planned Activities Counter',related='company_id.sh_display_planned_activities_counter',readonly=False)
    sh_display_completed_activities_counter = fields.Boolean('Completed Activities Counter',related='company_id.sh_display_completed_activities_counter',readonly=False)
    sh_display_overdue_activities_counter = fields.Boolean('Overdue Activities Counter',related='company_id.sh_display_overdue_activities_counter',readonly=False)
    sh_display_cancelled_activities_counter = fields.Boolean('Cancelled Activities Counter',related='company_id.sh_display_cancelled_activities_counter',readonly=False)
    sh_display_all_activities_table = fields.Boolean('All Activities Table',related='company_id.sh_display_all_activities_table',readonly=False)
    sh_display_planned_activities_table = fields.Boolean('Planned Activities Table',related='company_id.sh_display_planned_activities_table',readonly=False)
    sh_display_completed_activities_table = fields.Boolean('Completed Activities Table',related='company_id.sh_display_completed_activities_table',readonly=False)
    sh_display_overdue_activities_table = fields.Boolean('Overdue Activities Table',related='company_id.sh_display_overdue_activities_table',readonly=False)
    sh_display_cancelled_activities_table = fields.Boolean('Cancelled Activities Table',related='company_id.sh_display_cancelled_activities_table',readonly=False)
    sh_display_activity_reminder = fields.Boolean('Activity Reminder ?',related='company_id.sh_display_activity_reminder',readonly=False)
    sh_document_model = fields.Boolean('Display document model wise activity ?',related='company_id.sh_document_model',readonly=False)
    sh_document_model_ids = fields.Many2many('ir.model',string='Document Models',related='company_id.sh_document_model_ids',readonly=False)

    @api.onchange('sh_document_model')
    def onchange_sh_document_model(self):
        if self.sh_document_model:
            models = self.env['ir.model'].sudo().search([('state', '!=', 'manual')])
            document_models = []
            for model in models:
                if not model.model.startswith('ir.'):
                    document_models.append(model.id)
            return {'domain': {'sh_document_model_ids': [('id', 'in', document_models)]}}
        else:
            self.sh_document_model_ids = False
    
    def action_update_activity_data(self):
        activities = self.env['mail.activity'].sudo().search([('active','!=',False),('activity_cancel','=',False),('activity_done','=',False)])
        if activities:
            for activity in activities:
                activity.active = True
                activity.onchange_state()
    