from odoo import _, api, fields, models

class equip3WaMessageTemplate(models.Model):
    _name = 'wa.template.message'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    @api.model
    def _get_new_category(self):
        categories = [
            ('marketing','Marketing'),
            ('utility','Utility'),
            ('authentication','Authentication')
        ]

        return categories
    
    name = fields.Char()
    message = fields.Text()
    broadcast_template_id = fields.Many2one('qiscus.wa.template.content',string="Broadcast Template")
    namespace = fields.Char(related='broadcast_template_id.template_id.namespace')
    content = fields.Text(related='broadcast_template_id.content')
    wa_variable_ids = fields.One2many('wa.template.message.variable','wa_id', compute='_update_wa_variables', store=True)
    category = fields.Selection(selection=_get_new_category,default='utility')
    
    @api.onchange('category')
    def _onchange_category(self):
        for record in self:
            if record.broadcast_template_id  and record.category:
                if record.broadcast_template_id.category != record.category:
                    record.broadcast_template_id = False
    
    
    def action_test_template(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.test.template',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Whatsapp Test Template",
            'context':{'default_wa_id':self.id,'default_broadcast_template_id':self.broadcast_template_id.id},
            'target': 'new',
        }
    
    
    
    
    
    
    
    @api.model
    def default_get(self, fields):
        res = super(equip3WaMessageTemplate, self).default_get(fields)
        line_list = []
        line_list.append((0,0,{'name':"${applicant_name}",
                               'description':"Applicant Name"
                               }))
        
        line_list.append((0,0,{'name':"${survey_url}",
                               'description':"Survey or Test URL"
                               }))
        line_list.append((0,0,{'name':"${survey_name}",
                               'description':"Survey or Test Name"
                               }))
        line_list.append((0,0,{'name':"${br}",
                               'description':"Break Line"
                               }))
        
        line_list.append((0,0,{'name':"${job}",
                               'description':"Job position"
                               }))
        line_list.append((0,0,{'name':"${stage_before_technical}}",
                               'description':"Stage Before Technical"
                               }))
        line_list.append((0,0,{'name':"${recruiter_email}",
                               'description':"Recruiter Email"
                               }))
        line_list.append((0,0,{'name':"${recruiter_name}",
                               'description':"Recruiter Name"
                               }))
        line_list.append((0,0,{'name':"${applicant_id}",
                               'description':"Applicant ID"
                               }))
        
        res.update({'wa_variable_ids': line_list})
        return res

    @api.depends('name')
    def _update_wa_variables(self):
        var = []
        for record in self:
            line_list = []
            var = [data.name for data in record.wa_variable_ids]
        
            if "${applicant_name}" not in var:
                line_list.append((0,0,{'name':"${applicant_name}",
                                'description':"Applicant Name"
                                    }))
            if "${survey_url}" not in var:
                line_list.append((0,0,{'name':"${survey_url}",
                                    'description':"Survey or Test URL"
                                    }))
            if "${survey_name}" not in var:
                line_list.append((0,0,{'name':"${survey_name}",
                                    'description':"Survey or Test Name"
                                    }))
            if "${br}" not in var:
                line_list.append((0,0,{'name':"${br}",
                                    'description':"Break Line"
                                    }))
            if "${job}" not in var:
                line_list.append((0,0,{'name':"${job}",
                                    'description':"Job position"
                                    }))
            if "${stage_before_technical}}" not in var:
                line_list.append((0,0,{'name':"${stage_before_technical}}",
                                    'description':"Stage Before Technical"
                                    }))
            if "${recruiter_email}" not in var:
                line_list.append((0,0,{'name':"${recruiter_email}",
                                    'description':"Recruiter Email"
                                    }))
            if "${recruiter_name}" not in var:
                line_list.append((0,0,{'name':"${recruiter_name}",
                                    'description':"Recruiter Name"
                                    }))
            if "${applicant_id}" not in var:
                line_list.append((0,0,{'name':"${applicant_id}",
                                    'description':"Applicant ID"
                                    }))
            record.wa_variable_ids = line_list
        # if not res.wa_variable_ids:
        #     res.wa_variable_ids = line_list

    
    @api.model
    def create(self, vals_list):
        res = super(equip3WaMessageTemplate,self).create(vals_list)
        line_list = []
        line_list.append((0,0,{'name':"${applicant_name}",
                               'description':"Applicant Name"
                               }))
        
        line_list.append((0,0,{'name':"${survey_url}",
                               'description':"Survey or Test URL"
                               }))
        line_list.append((0,0,{'name':"${survey_name}",
                               'description':"Survey or Test Name"
                               }))
        line_list.append((0,0,{'name':"${br}",
                               'description':"Break Line"
                               }))
        
        line_list.append((0,0,{'name':"${job}",
                               'description':"Job position"
                               }))
        line_list.append((0,0,{'name':"${stage_before_technical}}",
                               'description':"Stage Before Technical"
                               }))
        line_list.append((0,0,{'name':"${recruiter_email}",
                               'description':"Recruiter Email"
                               }))
        line_list.append((0,0,{'name':"${recruiter_name}",
                               'description':"Recruiter Name"
                               }))
        line_list.append((0,0,{'name':"${applicant_id}",
                               'description':"Applicant ID"
                               }))
        
        if not res.wa_variable_ids:
            res.wa_variable_ids = line_list
        return res
    
    


class equip3WaMessageTemplateVariables(models.Model):
    _name = 'wa.template.message.variable'
    
    wa_id = fields.Many2one('wa.template.message',ondelete='cascade')
    name = fields.Char()
    description = fields.Char()
    
