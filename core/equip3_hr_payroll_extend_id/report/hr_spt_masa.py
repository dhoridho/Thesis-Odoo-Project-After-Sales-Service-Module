# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class HrSptMasa(models.Model):
    _name = 'hr.spt.masa'

    company_id = fields.Many2one('res.company', string='Company',default=lambda self:self.env.company.id)
    year = fields.Char('Year')
    month = fields.Char('Month')
    spt_type = fields.Many2one('hr.spt.type', string='SPT Type')
    spt_type_name = fields.Char('SPT Type Name')
    attachment = fields.Binary()
    attachment_fname = fields.Char(compute='get_attachment_fname')
 
 
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrSptMasa, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrSptMasa, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def name_get(self):
        result = []
        for rec in self:
            month_datetime = datetime.strptime(rec.month, "%B")
            month_number = month_datetime.month
            name = rec.company_id.name + ' ' + rec.spt_type.name  + ' ' + str('{:02d}'.format(month_number)) + rec.year
            result.append((rec.id, name))
        return result

    @api.depends('attachment')
    def get_attachment_fname(self):
        for record in self:
            if record.attachment:
                month_datetime = datetime.strptime(record.month, "%B")
                month_number = month_datetime.month
                record.attachment_fname = f"{record.company_id.name}_{record.spt_type.name}_{str('{:02d}'.format(month_number))}{record.year}"
            else:
                record.attachment_fname = ""