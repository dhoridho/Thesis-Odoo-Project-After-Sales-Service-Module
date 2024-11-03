from odoo import fields,api,models
from odoo.exceptions import ValidationError

class HashmicroCareerTransitionLetter(models.Model):
    _name = 'hr.career.transition.letter'
    _description="Career Transition Letter"
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char()
    letter_content = fields.Html()
    career_letter_ids = fields.One2many('hr.career.transition.variables','career_letter_id')
    
    
    
    
    
    
    # @api.model
    # def create(self, vals_list):
    #     res =  super().create(vals_list)
    #     model = self.env['ir.model'].search([('model','=','hr.career.transition')])
    #     if not model:
    #         raise ValidationError("model not found")
    #     dont_get = ('message_needaction','message_main_attachment_id','message_is_follower','message_ids','__last_update',
    #                 'activity_date_deadline','activity_exception_decoration','activity_exception_icon','activity_ids',
    #                 'activity_state','activity_summary','activity_type_icon','activity_type_id','activity_user_id',
    #                 'approval_matrix_ids','id','is_employee_sequence_number','is_hide_approve','is_hide_confirm','is_hide_reject'
    #                 ,'message_attachment_count','message_channel_ids','message_follower_ids','message_has_error','message_has_error_counter',
    #                 'message_has_sms_error','message_ids','message_is_follower','message_main_attachment_id',
    #                 'message_needaction','write_uid','write_date','website_message_ids','same_as_previous','status','message_unread_counter',
    #                 'message_unread','message_partner_ids','message_needaction_counter','my_activity_date_deadline')
    #     field = self.env['ir.model.fields'].search([('model_id','=',model.id),('name','not in',dont_get)])
    #     data = []
    #     for line in field:
    #         data.append((0,0,{'variable_name':f"$({line.name})",'description':line.field_description}))
    #     res.career_letter_ids = data
    #
    #
    #     return res
    
    @api.onchange('name')
    def _onchange_create_line_item(self):
        for rec in self:
            if not rec.career_letter_ids:
                model = self.env['ir.model'].search([('model', '=', 'hr.career.transition')])
                if not model:
                    raise ValidationError("model not found")
                dont_get = ('message_needaction', 'message_main_attachment_id', 'message_is_follower', 'message_ids',
                            '__last_update',
                            'activity_date_deadline', 'activity_exception_decoration', 'activity_exception_icon',
                            'activity_ids',
                            'activity_state', 'activity_summary', 'activity_type_icon', 'activity_type_id',
                            'activity_user_id',
                            'approval_matrix_ids', 'id', 'is_employee_sequence_number', 'is_hide_approve',
                            'is_hide_confirm', 'is_hide_reject'
                            , 'message_attachment_count', 'message_channel_ids', 'message_follower_ids',
                            'message_has_error', 'message_has_error_counter',
                            'message_has_sms_error', 'message_ids', 'message_is_follower', 'message_main_attachment_id',
                            'message_needaction', 'write_uid', 'write_date', 'website_message_ids', 'same_as_previous',
                            'status', 'message_unread_counter',
                            'message_unread', 'message_partner_ids', 'message_needaction_counter',
                            'my_activity_date_deadline')
                field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', 'not in', dont_get)])
                data = []
                for line in field:
                    data.append((0, 0, {'variable_name': f"$({line.name})", 'description': line.field_description}))
                rec.career_letter_ids = data

class HashmicroCareerTransitionLetterVariables(models.Model):
    _name = 'hr.career.transition.variables'
    variable_name = fields.Char()
    description = fields.Char()
    career_letter_id = fields.Many2one('hr.career.transition.letter')