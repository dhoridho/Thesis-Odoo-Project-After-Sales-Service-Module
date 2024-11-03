from odoo import fields,api,models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64


class ConstructionContractLetter(models.Model):
    _name = 'const.contract.letter'
    _description="Contract Letter"
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char()
    letter_content = fields.Html()
    career_letter_ids = fields.One2many('const.contract.variables','contract_letter_id')
    
    @api.model
    def create(self, vals_list):
        res =  super().create(vals_list)
        model = self.env['ir.model'].search([('model','=','sale.order.const')])
        if not model:
            raise ValidationError("model not found")
        # List of excluded fields
        dont_get = ('message_needaction','message_main_attachment_id','message_is_follower','message_ids','__last_update',
                    'activity_date_deadline','activity_exception_decoration','activity_exception_icon','activity_ids',
                    'activity_state','activity_summary','activity_type_icon','activity_type_id','activity_user_id',
                    'approval_matrix_ids','id','is_employee_sequence_number','is_hide_approve','is_hide_confirm','is_hide_reject'
                    ,'message_attachment_count','message_channel_ids','message_follower_ids','message_has_error','message_has_error_counter',
                    'message_has_sms_error','message_ids','message_is_follower','message_main_attachment_id',
                    'message_needaction','write_uid','write_date','website_message_ids','same_as_previous','status','message_unread_counter',
                    'message_unread','message_partner_ids','message_needaction_counter','my_activity_date_deadline','kanban_state','calendar_mismatch',
                    'career_tansition_id','create_uid','display_name','active','career_transition_id', 'access_token', 'access_url', 'access_warning', 
                    'adjustment_amount_global', 'adjustment_method_global', 'adjustment_scope', 'adjustment_section', 'adjustment_sub', 'adjustment_type', 
                    'adjustment_variable', 'address', 'report_contract_category', 'report_country', 'report_name', 'report_project_scope_id',
                    'report_retention_1_date', 'report_retention_2_date', 'report_street', 'report_tax', 'report_title', 'sale_limit_state_1_const', 'sale_limit_state_2_const',
                    'sale_limit_state_3_const', 'sale_limit_state_4_const', 'sale_limit_state_5_const', 'sale_limit_state_const', 'sale_state_1', 'sale_state', 'sale_state_const',
                    'scope_adjustment_ids', 'scope_discount_ids', 'section_adjustment_ids', 'section_discount_ids', 'section_ids', 'state_1', 'state_1_const', 'state_cancel', 'state_block',
                    'state_done', 'state_id', 'tag_ids', 'variable_ids', 'approval_matrix_line_id', 'approval_matrix_state', 'approval_matrix_state_1', 'approval_matrix_state_1_const', 
                    'approval_matrix_state_2_const', 'approval_matrix_state_3_const', 'approval_matrix_state_4_const', 'approval_matrix_state_5_const', 'approval_matrix_state_6_const',
                    'approval_matrix_state_7_const', 'approval_matrix_state_8_const', 'approval_matrix_state_const', 'approved_matrix_ids', 'approved_matrix_limit_ids', 'approved_matrix_limit_state_id',
                    'approved_matrix_sale_id', 'is_approval_matrix_filled', 'is_approve_button', 'is_approve_button_limit', 'is_customer_approval_matrix_const', 'is_direct_confirm', 'is_expired', 'is_quotation_cancel', 'is_over_limit_validation',
                    'is_limit_matrix_filled', 'limit_approval_matrix_line_id', 'limit_matrix_state_1_const', 'limit_matrix_state_2_const', 'limit_matrix_state_const', 'approving_matrix_limit_id', 'approving_matrix_sale_id',
                    'order_line_ids', 'type_name'
                    )
        field = self.env['ir.model.fields'].search([('model_id','=',model.id),('name','not in',dont_get)])
        data = []
        for line in field:
            data.append((0,0,{'variable_name':f"$({line.name})",'description':line.field_description}))
        res.career_letter_ids = data
            
        return res
    

class ConstructionContractVariables(models.Model):
    _name = 'const.contract.variables'
    _description = "Construction Contract Variables"

    variable_name = fields.Char()
    description = fields.Char()
    contract_letter_id = fields.Many2one('const.contract.letter')

