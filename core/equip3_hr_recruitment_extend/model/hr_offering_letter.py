from odoo import fields,api,models
from odoo.exceptions import ValidationError

class HrOfferingLetter(models.Model):
    _name = 'hr.offering.letter'
    _description="HR Offering Letter"
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char()
    email_template_id = fields.Many2one('mail.template', string="Email Template")
    wa_template_id = fields.Many2one('wa.template.message', string="WhatsApp Template")
    letter_content = fields.Html()
    letter_variable_ids = fields.One2many('hr.offering.letter.variables','letter_id')

    @api.model
    def create(self, vals_list):
        res = super(HrOfferingLetter,self).create(vals_list)
        line_list = []
        line_list.append((0,0,{'name':"${applicant_name}",
                            'description':"Applicant Name"
                            }))
        line_list.append((0,0,{'name':"${job_position}",
                            'description':"Job Position"
                            }))
        line_list.append((0,0,{'name':"${supervisor_name}",
                            'description':"Supervisor Name"
                            }))
        line_list.append((0,0,{'name':"${supervisor_job_position}",
                            'description':"Supervisor Job Position"
                            }))
        line_list.append((0,0,{'name':"${proposed_salary}",
                            'description':"Proposed Salary"
                            }))
        line_list.append((0,0,{'name':"${contract_period}",
                            'description':"Contract Period"
                            }))
        line_list.append((0,0,{'name':"${start_working_hours}",
                            'description':"Start Working Hours"
                            }))
        line_list.append((0,0,{'name':"${end_working_hours}",
                            'description':"End Working Hours"
                            }))
        line_list.append((0,0,{'name':"${start_working_days}",
                            'description':"Start Working Days"
                            }))
        line_list.append((0,0,{'name':"${end_working_days}",
                            'description':"End Working Days"
                            }))
        line_list.append((0,0,{'name':"${start_working_date}",
                            'description':"Start Working Date"
                            }))
        line_list.append((0,0,{'name':"${hr_manager_name}",
                            'description':"Human Resource Manager Name"
                            }))
        line_list.append((0,0,{'name':"${current_date}",
                            'description':"Current Date"
                            }))
        
        if not res.letter_variable_ids:
            res.letter_variable_ids = line_list
        return res
    
    @api.onchange('name')
    def _onchange_create_line_item(self):
        for rec in self:
            rec.letter_variable_ids = [(5,0,0)]
            line_list = []
            line_list.append((0,0,{'name':"${applicant_name}",
                                'description':"Applicant Name"
                                }))
            line_list.append((0,0,{'name':"${job_position}",
                                'description':"Job Position"
                                }))
            line_list.append((0,0,{'name':"${supervisor_name}",
                                'description':"Supervisor Name"
                                }))
            line_list.append((0,0,{'name':"${supervisor_job_position}",
                                'description':"Supervisor Job Position"
                                }))
            line_list.append((0,0,{'name':"${proposed_salary}",
                                'description':"Proposed Salary"
                                }))
            line_list.append((0,0,{'name':"${contract_period}",
                                'description':"Contract Period"
                                }))
            line_list.append((0,0,{'name':"${start_working_hours}",
                                'description':"Start Working Hours"
                                }))
            line_list.append((0,0,{'name':"${end_working_hours}",
                                'description':"End Working Hours"
                                }))
            line_list.append((0,0,{'name':"${start_working_days}",
                                'description':"Start Working Days"
                                }))
            line_list.append((0,0,{'name':"${end_working_days}",
                                'description':"End Working Days"
                                }))
            line_list.append((0,0,{'name':"${start_working_date}",
                                'description':"Start Working Date"
                                }))
            line_list.append((0,0,{'name':"${hr_manager_name}",
                                'description':"Human Resource Manager Name"
                                }))
            line_list.append((0,0,{'name':"${current_date}",
                                'description':"Current Date"
                                }))
            rec.letter_variable_ids = line_list

class HrOfferingLetterVariables(models.Model):
    _name = 'hr.offering.letter.variables'

    letter_id = fields.Many2one('hr.offering.letter', ondelete='cascade')
    name = fields.Char()
    description = fields.Char()