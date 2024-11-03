from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, date, timedelta
from odoo.http import request
from odoo import http

class CustomerProductTemplate(models.Model):
    _name = 'customer.product.template'
    _description = "Customer Product Template"
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True, domain="[('company_id','=', company_id),('is_customer','=',True)]")
    creation_date = fields.Datetime(string='Creation Date', default=datetime.today())
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user.id)
    company_id =fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id.id)
    line_ids = fields.One2many('customer.product.template.line', 'customer_product_template_id', string='Brand')
    readonly_customer = fields.Boolean("Readonly")

    _sql_constraints = [
        ('customer_unique', 'unique(customer_id,company_id)', 'Customer must be unique!'),
    ]

    @api.model
    def create(self, vals):
        vals['readonly_customer'] = True
        res = super().create(vals)
        return res

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.line_ids:
                line.sequence = current_sequence
                current_sequence += 1

class CustomerProductTemplateLine(models.Model):
    _name = 'customer.product.template.line'
    _description = "Customer Product Template Line"

    @api.model
    def _domain_res_customer(self):
        return [('company_id', '=', self.env.company.id), ('is_customer','=', True)]

    customer_product_template_id = fields.Many2one('customer.product.template', string='Customer Product Template')
    sequence = fields.Integer(string="No")
    company_id =fields.Many2one('res.company', related='customer_product_template_id.company_id')
    res_sequence = fields.Integer(string="No.", related="sequence", readonly=True, store=True)
    product_template_id = fields.Many2one('product.template', string='Product')
    product_id = fields.Many2one('product.product', string='Product')
    product_label = fields.Char('Product Label', required=True)
    res_product_label = fields.Char('Product Label', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', related='customer_product_template_id.customer_id')
    res_customer_id = fields.Many2one('res.partner', string='Customer', domain=_domain_res_customer)
    from_customer = fields.Boolean('From Customer')
    from_product = fields.Boolean('From Product')
    from_product_template = fields.Boolean('From Product Template')

    _sql_constraints = [
        ('product_unique', 'unique(customer_product_template_id,company_id)', 'Customer must be unique!'),
    ]

    @api.onchange('product_id')
    def check_product(self):
        for rec in self:
            self.env.context = dict(self.env.context)
            if 'line_ids' not in self.env.context:
                self.env.context.update({
                    'line_ids': rec.customer_product_template_id.line_ids,
                })
            if not rec.customer_product_template_id:
                rec.customer_product_template_id = self.env['customer.product.template'].search([('customer_id','=', self.env.context['default_customer_id'])])
                rec.res_sequence = rec.sequence = len(rec.customer_product_template_id.line_ids) + 1
            product_ids = rec.customer_product_template_id.line_ids.filtered(lambda x: x.res_sequence != rec.res_sequence).mapped('product_id').ids
            if rec.product_id.id in product_ids:
                raise ValidationError("Product has been selected!")
            # rec.product_template_id = rec.product_id.product_tmpl_id if rec.product_id.product_tmpl_id.product_variant_id.id == rec.product_id.id else False
    
    @api.onchange('res_customer_id')
    def check_customer(self):
        for rec in self:
            if not 'default_from_product' in self.env.context and not 'default_from_product_template' in self.env.context:
                self.env.context = dict(self.env.context)
                if 'line_ids' not in self.env.context:
                    self.env.context.update({
                        'line_ids': rec.customer_product_template_id.line_ids,
                    })
                if not rec.customer_product_template_id:
                    rec.customer_product_template_id = self.env['customer.product.template'].search([('customer_id','=', rec.res_customer_id.id)])
                    rec.res_sequence = rec.sequence = len(rec.customer_product_template_id.line_ids) + 1
                customer_ids = rec.customer_product_template_id.line_ids.filtered(lambda x: x.res_sequence != rec.res_sequence).mapped('res_customer_id').ids
                if rec.customer_id.id in customer_ids:
                    raise ValidationError("Customer has been selected!")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # customer_credit_limit = self.env['ir.config_parameter'].sudo().get_param('customer_credit_limit', 1000000)
        # res['customer_credit_limit'] = customer_credit_limit
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'line_ids' in context_keys:
                if len(self._context.get('line_ids')) > 0:
                    next_sequence = len(self._context.get('line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    def unlink(self):
        customer_product_template_id = self.customer_product_template_id
        res = super().unlink()
        customer_product_template_id._reset_sequence()
        return res

    def create_customer_product_template(self, customer_id):
        customer_product_template_id = self.env['customer.product.template'].create({
            'customer_id': customer_id.id
        })
        return customer_product_template_id

    def get_customer_product_template_id(self):
        customer_product_template_id = self.env['customer.product.template'].search([('customer_id','=',self.res_customer_id.id)])
        if not customer_product_template_id:
            customer_product_template_id = self.create_customer_product_template(self.res_customer_id)
            self.sequence = 1
        else:
            self.sequence = len(customer_product_template_id) + 1
        self.customer_product_template_id = customer_product_template_id.id


    @api.model
    def create(self, vals):
        if 'from_product_template' in vals:
            vals['product_label'] = vals['res_product_label']
        else:
            vals['res_product_label'] = vals['product_label']
        res = super().create(vals)
        if not res.res_product_label:
            res.res_product_label = res.product_label
        # create from cust
        if 'from_customer' in vals:
            if not vals['customer_product_template_id']:
                res.get_customer_product_template_id()
                res.check_product()
        # create from prod temp
        elif 'from_product_template' in vals:
            res.get_customer_product_template_id()
            if not res.product_id:
                res.product_id = res.product_template_id.product_variant_id
            res.create_all_variant(res.product_id,res.product_template_id.product_variant_ids,res.customer_product_template_id)
            res.check_product()
        elif 'from_product' in vals:
            res.get_customer_product_template_id()
            res.check_product()
        if not self.env.context.get("keep-line_sequence", False):
            res.customer_product_template_id._reset_sequence()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'res_product_label' in vals:
            if 'product.template' in request.httprequest.url:
                self._cr.execute("""UPDATE customer_product_template_line SET product_label = %s,res_product_label = %s WHERE product_id in %s and customer_product_template_id = %s""", (self.res_product_label,self.res_product_label,tuple(self.product_template_id.product_variant_ids.ids),self.customer_product_template_id.id))
                self._cr.commit()
        return res

    def create_all_variant(self, variant_id, variant_ids, customer_product_template_id):
        seq = 2
        for rec in variant_ids:
            if rec.id != variant_id.id:
                self.env['customer.product.template.line'].create({
                    'sequence': seq,
                    'product_id': rec.id,
                    'product_label': self.product_label,
                    'res_product_label': self.res_product_label,
                    'res_customer_id': self.res_customer_id.id,
                    'customer_product_template_id': customer_product_template_id.id,
                    'from_product_template': True
                })
                seq += 1
