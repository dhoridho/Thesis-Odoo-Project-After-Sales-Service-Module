from odoo import _, api, fields, models
from datetime import date, datetime
from odoo.exceptions import ValidationError

class ThrRule(models.Model):
    _name = 'thr.rule'

    name = fields.Char('Name', required=True)
    date = fields.Date('Payment Date', required=True)
    year = fields.Char('Year', compute='_compute_year', store=True)
    cut_off_date = fields.Date('Cut Off Date', required=True)
    minimun_joined = fields.Integer('Minimum Joined', default=1, required=True)
    additional_rate = fields.Boolean('Additional rate', default=False)
    thr_additional_rate = fields.Float('THR Additional Rate (%)')
    yos_after = fields.Integer('YoS After')
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(ThrRule, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(ThrRule, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.depends('date')
    def _compute_allowed_employee_ids(self):
        for rec in self:
            if rec.date:
                year = datetime.strptime(str(self.date), '%Y-%m-%d').date().year
                thr_rule = self.sudo().search([('year', '=', year)])
                employee_thr = [x.id for x in thr_rule.employee_ids]
                rec.allowed_employee_ids = self.env['hr.employee'].search([('id', 'not in', employee_thr),('company_id','=',self.company_id.id)])
            else:
                rec.allowed_employee_ids = self.env['hr.employee'].search([('id', '=', -1),('company_id','=',self.company_id.id)])

    allowed_employee_ids = fields.Many2many('hr.employee', compute='_compute_allowed_employee_ids')
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain="[('id', 'in', allowed_employee_ids)]")

    @api.depends('date')
    def _compute_year(self):
        for res in self:
            if res.date:
                year = datetime.strptime(str(res.date), '%Y-%m-%d').date().year
                res.year = year
            else:
                res.year = False

    @api.constrains('minimun_joined')
    def constrains_minimun_joined(self):
        for res in self:
            if res.minimun_joined <= 0:
                raise ValidationError(_('Minimum Joined must be greater than 0.'))

    @api.onchange('additional_rate')
    def onchange_additional_rate(self):
        for res in self:
            if not res.additional_rate:
                res.thr_additional_rate = 0.0
                res.yos_after = 0

    @api.constrains('additional_rate','thr_additional_rate')
    def constrains_thr_additional_rate(self):
        for res in self:
            if res.additional_rate and res.thr_additional_rate <= 0:
                raise ValidationError(_('THR Additional Rate must be greater than 0.'))
    
    @api.constrains('additional_rate','yos_after')
    def constrains_yos_after(self):
        for res in self:
            if res.additional_rate and res.yos_after <= 0:
                raise ValidationError(_('YoS must be greater than 0.'))