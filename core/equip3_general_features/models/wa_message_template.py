import json
from odoo import _, api, fields, models
import re
from odoo.exceptions import ValidationError

class equip3MasterMessageTemplate(models.Model):
    _name = 'master.template.message'
    _description = 'Master Template Message'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char()
    message = fields.Text()
    broadcast_template_id = fields.Many2one('qiscus.wa.template.content',string="Broadcast Template")
    namespace = fields.Char(related='broadcast_template_id.template_id.namespace')
    content = fields.Text(related='broadcast_template_id.content')
    wa_variable_ids = fields.Many2many('qiscus.wa.variable')
    category = fields.Selection([('marketing','Marketing'),('utility','Utility'),('authentication','Authentication')],default='utility')
    variable_category_id = fields.Many2one('qiscus.wa.variable.category')
    use_image_file = fields.Boolean(default=False)
    use_header = fields.Boolean(default=False)
    header_type = fields.Selection([('text','Text'),('media','Media')])
    header_text = fields.Text()
    link_file = fields.Char()
    file_type = fields.Selection([('image','Image'),('document','Document'),('video','Video')])
    message_line_ids = fields.One2many('master.message.qiscuss','template_id')
    
    
    @api.onchange('broadcast_template_id')
    def onchange_broadcast_template_id(self):
        for data in self:
            if data.broadcast_template_id.is_use_header_variable:
                data.use_header = True
                if data.broadcast_template_id.header_type == 'text':
                    data.header_type =  data.broadcast_template_id.header_type
                if data.broadcast_template_id.header_type != 'text':
                    data.header_type = 'media'
                    data.file_type = data.broadcast_template_id.header_type
                    match = re.search(r'({.*})', data.content)
                    if match:
                        json_string = match.group(1)
                        # Parse the string to get the dictionary
                        data_json = json.loads(json_string)
                        data.link_file = data_json[data.broadcast_template_id.header_type]['link']

            else:
                data.use_header = False
    
    
    @api.model
    def create(self, vals_list):
        res =  super(equip3MasterMessageTemplate,self).create(vals_list)
        res._onchange_variable_category_id()
        
        if res.content and res.message_line_ids:
            matches = re.findall(r'{{\d+}}', res.content)
            result_list = []
            result_list.extend(matches)
        if res.message_line_ids:
            seq = -1
            for line in res.message_line_ids:
                seq +=1
                line.sequence = seq
                
            
            # if len(result_list) != len(res.message_line_ids):
            #     raise ValidationError("The Total message is less or more than the number of variables in the content.")

            
        
        return res
    
    def write(self, vals):
        res =  super(equip3MasterMessageTemplate,self).write(vals)
        if self.content and self.message_line_ids:
            matches = re.findall(r'{{\d+}}', self.content)
            result_list = []
            result_list.extend(matches)
        if self.message_line_ids:
            seq = -1
            for line in self.message_line_ids:
                seq +=1
                line.sequence = seq
            
            # if len(result_list) != len(self.message_line_ids):
            #     raise ValidationError("The Total message is less or more than the number of variables in the content.")
        
        return res
    
    
    @api.onchange('variable_category_id')
    def _onchange_variable_category_id(self):
        for data in self:
            if data.variable_category_id:
                variable_ids = self.env['qiscus.wa.variable'].search([('category_id','=',data.variable_category_id.id)])
                if variable_ids:
                    if data.wa_variable_ids:
                        data.wa_variable_ids = [(6,0,[])]
                    variable_to_assign = []
                    for line in variable_ids:
                        variable_to_assign.append(line.id)
                    data.wa_variable_ids = [(6,0,variable_to_assign)]
                
    
    
    @api.onchange('category')
    def _onchange_category(self):
        for record in self:
            if record.broadcast_template_id  and record.category:
                if record.broadcast_template_id.category != record.category:
                    record.broadcast_template_id = False
    
    
    def action_test_template(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'master.test.template',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Whatsapp Test Template",
            'context':{'default_wa_id':self.id,'default_broadcast_template_id':self.broadcast_template_id.id},
            'target': 'new',
        }
        




class equip3WaMessageTemplateVariables(models.Model):
    _name = 'qiscus.wa.variable'
    _description = 'Qiscus WhatsApp Variable'
    
    name = fields.Char()
    description = fields.Char()
    category_id = fields.Many2one('qiscus.wa.variable.category')
    model_id = fields.Many2one(comodel_name='ir.model', string='Model', ondelete='cascade')
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field', ondelete='cascade')
    special_var = fields.Boolean(default=False)
    
    @api.model
    def create(self, vals_list):
        res =  super(equip3WaMessageTemplateVariables,self).create(vals_list)
        message_to_update = self.env['master.template.message'].sudo().search([('variable_category_id','=',res.category_id.id)])
        if message_to_update:
            for msg in message_to_update:
                msg._onchange_variable_category_id()
        
        return res

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.model_id:
            return {
                'domain': {
                    'field_id': [('model_id', '=', self.model_id.id)]
                }
            }
        else:
            return {
                'domain': {
                    'field_id': []
                }
            }
    
    


class qiscusWaVariableCategory(models.Model):
    _name = 'qiscus.wa.variable.category'
    _description = 'Qiscus WhatsApp Variable Category'
    
    name = fields.Char()
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    
    

class equip3MasterMessageQiscuss(models.Model):
    _name = 'master.message.qiscuss'
    _order = 'sequence asc'
    
    template_id = fields.Many2one('master.template.message')
    sequence = fields.Integer()
    sequence_show = fields.Char(compute='_compute_sequence')
    message = fields.Text()
    
    
    
    @api.depends('sequence')
    def _compute_sequence(self):
        for data in self:
            if not data.id:
                data.sequence_show =  ''
            else:
                data.sequence_show = data.sequence + 1
                
    
    
    
    
    
    
    
    
    
