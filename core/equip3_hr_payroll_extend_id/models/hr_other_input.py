# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrOtherInputs(models.Model):
    _name = 'hr.other.inputs'
    _description = "HR Other Inputs"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    input_type = fields.Selection([
            ('manual_entries', 'Manual Entries'),
            ('get_from_other_object', 'Get from Other Object')
        ], string="Input Type", default='manual_entries', required=True)
    model_id = fields.Many2one('ir.model', string='Model',
                              domain="[('access_ids','!=',False),('transient','=',False),"
                                     "('model','not ilike','base_import%'),('model','not ilike','ir.%'),"
                                     "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                     "('model','!=','mail.thread'),('model','not ilike','hr_other%')]")
    calculate_type = fields.Selection([
            ('count', 'Count'),
            ('sum', 'Sum'),
            ('average', 'Average')
        ], string="Calculate Type", default='count')
    record_field = fields.Many2one('ir.model.fields', string='Record Field',
                                   domain="[('model_id','=',model_id),('name','!=','id'),('name','!=','sequence'),"
                                          "('store','=',True),'|','|',"
                                          "('ttype','=','integer'),('ttype','=','float'),"
                                          "('ttype','=','monetary')]")
    domain_filter = fields.Text(string='Domain Filter', help='Please create a syntax in here if you need to show only specific data records from your Models')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 copy=False, default=lambda self: self.env['res.company']._company_default_get())
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], string='Status')
    is_hide_confirm = fields.Boolean(default=True)
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrOtherInputs, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrOtherInputs, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def create(self, vals):
        res = super(HrOtherInputs, self).create(vals)
        res.state = 'draft'
        res.is_hide_confirm = False
        res.message_post(body=_('Status: Draft'))
        return res

    def unlink(self):
        for record in self:
            if record.state in ('confirm'):
                raise ValidationError("Only Draft status can be deleted")
        data = super(HrOtherInputs, self).unlink()
        return data

    @api.constrains('code')
    def check_code(self):
        for record in self:
            if record.code:
                check_name = self.search([('code', '=', record.code), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Code must be unique!")

    def action_generate_entries(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.other.inputs.generate.entries",
            "view_mode": 'form',
            "view_type": 'form',
            'view_id': self.env.ref("equip3_hr_payroll_extend_id.view_generate_entries_form").id,
            "name": "Genarate Entries",
            "target": "new",
            "context": {
                'default_hr_other_input_id': self.id
            },
        }

    def to_confirm(self):
        for rec in self:
            rec.state = "confirm"
            rec.is_hide_confirm = True
            rec.message_post(body=_('Status: Draft -> Confirm'))