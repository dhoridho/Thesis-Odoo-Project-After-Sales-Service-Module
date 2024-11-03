from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    summary_count = fields.Integer(compute='compute_summary_count', readonly=True, store=True)
    summary_ids = fields.One2many('calendar.meeting.summary','calendar_events_id', string = 'Meeting Summary')

    @api.depends('summary_ids')
    def compute_summary_count(self):
        for record in self:
            record.summary_count = len(record.summary_ids)
            if record.summary_count > 0 and record.state == 'meeting':
                record.state = 'done'
            elif record.summary_count == 0:
                if record.sign_out is not True and record.state == 'done':
                    record.state = 'meeting'

    def action_open_calendar_meeting(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        context.update({'default_viewer_ids': [(6, 0, self.partner_ids.ids)],'default_calendar_events_id': self.id, 'default_tags_ids':[(6,0,self.categ_ids.ids)]})
        return {
            'name': _('Meeting Summary'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'calendar.meeting.summary',
            'type': 'ir.actions.act_window',
            'domain': [('calendar_events_id','=',self.id)],
            'context': context,
            'target': 'current',
        }


class CalendarEventTypeInherit(models.Model):
    _inherit = 'calendar.event.type'

    is_meeting_summary_required = fields.Boolean(string='Meeting Summary Required')
    summary_template_id = fields.Many2one(comodel_name='summary.template', string='Summary Template')
    summary = fields.Html(string='Summary')
    is_hide_template = fields.Boolean(string='Hide Template', compute="_compute_hide_template")
    
    @api.depends('name','is_meeting_summary_required')
    def _compute_hide_template(self):
        for i in self:
            is_meeting_summary = bool(self.env['ir.config_parameter'].sudo().get_param(
                'equip3_crm_meeting_summary.is_meeting_summary')) or False
            if is_meeting_summary:
                is_use_template_meeting_summary = bool(self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_crm_meeting_summary.is_use_template_meeting_summary')) or False
                i.is_hide_template = not is_use_template_meeting_summary
                if not is_use_template_meeting_summary:
                    i.summary_template_id = False
            else:
                i.is_hide_template = True
                i.summary_template_id = False
    
    
    
    
    

    
    
