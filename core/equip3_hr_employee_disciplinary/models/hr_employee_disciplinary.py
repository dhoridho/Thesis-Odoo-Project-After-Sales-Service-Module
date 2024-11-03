import base64
import os
import subprocess
import tempfile
from collections import OrderedDict
from contextlib import closing
from datetime import timedelta, datetime
from lxml import etree
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, tools
from odoo.addons.base.models.ir_actions_report import _get_wkhtmltopdf_bin
from odoo.exceptions import ValidationError, _logger, UserError
from odoo.sql_db import TestCursor
from odoo.tools import config


class Equip3HremployeeDisciplinary(models.Model):
    _name = 'hr.employee.disciplinary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Disciplinary'
    _rec_name = 'employee_id'
    _order = 'dicliplined_date desc'
    
    def _default_employee(self):
        return self.env.user.employee_id
    disciplinary_number = fields.Char("Disciplinary Number")
    status = fields.Selection([('draft','Draft'),('confirmed','On Going'),('expired','Expired')],default='draft')
    employee_id = fields.Many2one('hr.employee',"Employee",default=_default_employee)
    job_position = fields.Many2one('hr.job',related='employee_id.job_id')
    department_id = fields.Many2one('hr.department',related='employee_id.department_id')
    discliplinary_stage = fields.Many2one('hr.employee.disciplinary.stage',"Disciplinary Stage")
    dicliplined_date = fields.Date("Disciplined Date")
    valid_for_months = fields.Integer(related='discliplinary_stage.valid_for_months')
    valid_until = fields.Date(compute='get_valid_until',store=True)
    reason_of_disciplinary= fields.Text()
    attachment = fields.Binary()
    history_ids = fields.One2many('hr.employee.disciplinary.history','employee_disciplinary_id')
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id,readonly=True)
    branch_id = fields.Many2one('res.branch',"Branch",domain=[('company_id','=',company_id)])
    is_hide_confirm = fields.Boolean()
    document_fname = fields.Char(compute='get_fname')
    employee_domain_ids = fields.Many2many('hr.employee',string="Employee Domain",compute='_get_employee_domain_ids')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HremployeeDisciplinary, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HremployeeDisciplinary, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('employee_id')
    def _get_employee_domain_ids(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
                employee_ids = []
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                record.employee_domain_ids = employee_ids
            else:
                employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                employee_ids = []
                if employee:
                    for record_employee in employee:
                        employee_ids.append(record_employee.id)
                record.employee_domain_ids = employee_ids
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3HremployeeDisciplinary, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
           
            
        return res
    
    
    
    
    def custom_menu(self):
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Disciplinary',
                'res_model': 'hr.employee.disciplinary',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)]
            }
        elif  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            employee_ids = []
            my_employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
            if my_employee:
                employee_ids.append(my_employee.id)
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Disciplinary',
                'res_model': 'hr.employee.disciplinary',
                'view_mode': 'tree,form',
                'domain': [('employee_id', 'in', employee_ids)]
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Disciplinary',
                'res_model': 'hr.employee.disciplinary',
                'view_mode': 'tree,form'
            }
    
    @api.onchange('employee_id')
    def _get_history_disciplinary(self):
        for record in self:
            history = []
            if record.employee_id:
                if record.employee_id.disciplinary_stage_ids:
                    if record.history_ids:
                        line_remove = []
                        for remove in record.history_ids:
                            line_remove.append((2,remove.id))
                        record.history_ids = line_remove
                    for line in record.employee_id.disciplinary_stage_ids:     
                        history.append((0,0,{'dicliplined_date':line.dicliplined_date,'discliplinary_stage':line.discliplinary_stage.id,'valid_until':line.valid_until,'reason_of_disciplinary':line.reason_of_disciplinary,'status':line.status}))
                    record.history_ids = history
                else:
                    record.history_ids = False
            else:
                 record.history_ids = False
                
                    
    @api.model
    def ir_cron_update_status(self):
       disciplinary = self.search([('valid_until','<',datetime.now().date())])
       if disciplinary:
           for record in disciplinary:
               record.status = 'expired'




    @api.depends('attachment')
    def get_fname(self):
        for record in self:
            if record.attachment:
                record.document_fname = f"{record.employee_id.name}-{record.disciplinary_number}"
            else:
                record.document_fname = ""

    @api.depends('valid_for_months','dicliplined_date')
    def get_valid_until(self):
        for record in self:
            if record.valid_for_months and record.dicliplined_date:
                record.valid_until = record.dicliplined_date + relativedelta(months=record.valid_for_months)
            else:
                record.valid_until = False

    def print_on_page(self):
        for record in self:
            sequence = self.env['ir.sequence'].search([('code','=',record._name)])
            if not sequence:
                raise ValidationError("Sequence for Disciplinary not found")
            split_sequence = str(sequence.next_by_id()).split('/')
            disciplinary_number = F"{split_sequence[1]}/SP-{record.discliplinary_stage.disciplinary_stage}/{split_sequence[0]}"
            record.disciplinary_number = disciplinary_number
            record.is_hide_confirm = True
            record.status = 'confirmed'
            dicliplined_date = datetime.strptime(str(record.dicliplined_date), "%Y-%m-%d")
            dicliplined_date_string = datetime(dicliplined_date.year, dicliplined_date.month,
                                               dicliplined_date.day).strftime("%d %B %Y")
            temp = record.discliplinary_stage.letter_content
            letter_content_employee_name = record.discliplinary_stage.letter_content.replace("@employee_name", record.employee_id.name)
            letter_content_company_name = str(letter_content_employee_name).replace('@company_name', record.employee_id.company_id.name)
            letter_content_company_address = str(letter_content_company_name).replace('@company_address', record.employee_id.company_id.street)
            letter_content_disciplinary_number = str(letter_content_company_address).replace('@disciplinary_number', disciplinary_number)
            letter_content_job_position = str(letter_content_disciplinary_number).replace('@job_position', record.employee_id.job_id.name if record.employee_id.job_id else "")
            letter_content_valid_for_months = str(letter_content_job_position).replace('@valid_for_months', str(record.valid_for_months))
            letter_disciplinary_date = str(letter_content_valid_for_months).replace('@disciplinary_date', dicliplined_date_string)
            letter_reason_of_disciplinary = str(letter_disciplinary_date).replace('@reason_of_disciplinary', record.reason_of_disciplinary)
            record.discliplinary_stage.letter_content = letter_reason_of_disciplinary
            data = record.discliplinary_stage.letter_content
            record.discliplinary_stage.letter_content = temp
            return data
            


    def set_confirm(self):
        for record in self:
            sequence = self.env['ir.sequence'].search([('code','=',record._name)])
            if not sequence:
                raise ValidationError("Sequence for Disciplinary not found")
            split_sequence = str(sequence.next_by_id()).split('/')
            disciplinary_number = F"{split_sequence[1]}/SP-{record.discliplinary_stage.disciplinary_stage}/{split_sequence[0]}"
            record.disciplinary_number = disciplinary_number
            record.is_hide_confirm = True
            record.status = 'confirmed'
            dicliplined_date = datetime.strptime(str(record.dicliplined_date), "%Y-%m-%d")
            dicliplined_date_string = datetime(dicliplined_date.year, dicliplined_date.month,
                                               dicliplined_date.day).strftime("%d %B %Y")
            temp = record.discliplinary_stage.letter_content
            letter_content_employee_name = record.discliplinary_stage.letter_content.replace("@employee_name", record.employee_id.name)
            letter_content_company_name = str(letter_content_employee_name).replace('@company_name', record.employee_id.company_id.name)
            letter_content_company_address = str(letter_content_company_name).replace('@company_address', record.employee_id.company_id.street)
            letter_content_disciplinary_number = str(letter_content_company_address).replace('@disciplinary_number', disciplinary_number)
            letter_content_job_position = str(letter_content_disciplinary_number).replace('@job_position', record.employee_id.job_id.name if record.employee_id.job_id else "")
            letter_content_valid_for_months = str(letter_content_job_position).replace('@valid_for_months', str(record.valid_for_months))
            letter_disciplinary_date = str(letter_content_valid_for_months).replace('@disciplinary_date', dicliplined_date_string)
            letter_reason_of_disciplinary = str(letter_disciplinary_date).replace('@reason_of_disciplinary', record.reason_of_disciplinary)
            record.discliplinary_stage.letter_content = letter_reason_of_disciplinary
            pdf = self.env.ref('equip3_hr_employee_disciplinary.equip3_hr_employee_disciplinary_attachment_report')._render_qweb_pdf([record.id])
            attachment = base64.b64encode(pdf[0])
            record.attachment = attachment

            if record.discliplinary_stage.send_an_email:
                template = self.env.ref('equip3_hr_employee_disciplinary.mail_hr_employee_disciplinary')
                template.body_html = letter_reason_of_disciplinary
                ctx = self.env.context.copy()
                ctx.update({
                    'email_to': record.employee_id.work_email,
                })

                mail_id = self.env['mail.template'].browse(template.id).with_context(ctx).send_mail(record.id)
                record.discliplinary_stage.letter_content = temp
                return self.env['mail.mail'].browse(mail_id).send()



class Equip3HremployeeDisciplinaryStage(models.Model):
    _name = 'hr.employee.disciplinary.stage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Disciplinary Stage'
    _rec_name = 'disciplinary_name'
    disciplinary_name = fields.Char("Disciplinary Name",required=True)
    disciplinary_stage = fields.Integer("Disciplinary Stage",required=True)
    valid_for_months = fields.Integer("Valid for Months",required=True)
    send_an_email = fields.Boolean("Send an Email",default=True)
    user_variables = fields.Text("User Variables")
    letter_content = fields.Html("Letter Content")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, readonly=True)
    branch_id = fields.Many2one('res.branch',"Branch",domain=[('company_id','=',company_id)])
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HremployeeDisciplinaryStage, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HremployeeDisciplinaryStage, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3HremployeeDisciplinaryStage, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
           
            
        return res
    


class Equip3HremployeeDisciplinaryHistory(models.Model):
    _name = 'hr.employee.disciplinary.history'
    _description = 'Employee Disciplinary'
    employee_disciplinary_id = fields.Many2one('hr.employee.disciplinary')
    status = fields.Selection([('draft','Draft'),('confirmed','On Going'),('expired','Expired')],default='draft')
    discliplinary_stage = fields.Many2one('hr.employee.disciplinary.stage',"Disclipnary Stage")
    dicliplined_date = fields.Date("Disciplined Date")
    valid_until = fields.Date()
    reason_of_disciplinary= fields.Text()
   




