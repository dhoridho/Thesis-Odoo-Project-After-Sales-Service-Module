# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from lxml import etree

class CompetenciesLevel(models.Model):
    _name = 'competencies.level'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Comptencies Level'
    
    name = fields.Char()
    description = fields.Text()
    training_required_ids = fields.Many2many('training.courses', string='Training Required')
    line_ids = fields.One2many('competencies.level.line','competencies_id')
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(CompetenciesLevel, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)   
        elif self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res





class CompetenciesLevelLine(models.Model):
    _name = 'competencies.level.line'
    _rec_name = 'level_name'
    _description = 'Comptencies Level Line'
    competencies_id =  fields.Many2one('competencies.level',required=True, ondelete="cascade")
    sequence = fields.Integer()
    competency_score = fields.Integer(string='Score', required=True)
    name = fields.Char(string='Level', required=True)
    level_name = fields.Char(compute='_compute_level_name', store=True)
    description = fields.Text(required=False)
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(CompetenciesLevelLine, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)   
        elif self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
    
    
    @api.depends('name','competency_score')
    def _compute_level_name(self):
        for record in self:
            if record.name and record.competency_score:
                record.level_name = f"{record.competency_score} - {record.name}"
            else:
                record.level_name = ''
    
    def write(self, vals):
        if 'level' in vals:
            for record in self:
                if record.search([('competencies_id','=',record.competencies_id.id),('level','=',vals['level']),('id','!=',record.id)]):
                    raise ValidationError("cannot set same level in one competencies")
                
        res = super(CompetenciesLevelLine,self).write(vals)
        
        return res

    
    @api.model   
    def create(self, vals_list):
        res =  super(CompetenciesLevelLine,self).create(vals_list)
        for record in res:
            if record.search([('competencies_id','=',record.competencies_id.id),('name','=',record.name),('id','!=',record.id)]):
                raise ValidationError("cannot set same level in one competencies")
        
        return res