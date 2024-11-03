import json
from odoo import models, fields, api, tools, _
from odoo.osv import expression
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    _rec_name = 'product_tmpl_id'

    is_secret_bom = fields.Boolean(string='Secret BoM')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super(MrpBom, self).fields_get(allfields=allfields, attributes=attributes)
        if 'is_secret_bom' not in result:
            return result
        user_secret_bom = self.env['ir.rule']._has_secret_bom_groups()
        user_secret_manager = self.env.user.has_group('equip3_manuf_inventory.group_mrp_secret_manager')
        if not user_secret_bom:
            result['is_secret_bom']['searchable'] = False
            result['is_secret_bom']['sortable'] = False
        if not user_secret_manager:
            result['is_secret_bom']['readonly'] = True
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if not self.env['ir.rule']._has_secret_product_groups():
            domain = domain or []
            new_domain = []
            for arg in domain:
                if isinstance(arg, list) or isinstance(arg, tuple):
                    field, operator, value = arg
                    if field == self._rec_name:
                        new_domain += [
                            '|', 
                                '&', 
                                    ('product_tmpl_id.is_secret_product', '=', False), 
                                    (field, operator, value),
                                '&',
                                    ('product_tmpl_id.is_secret_product', '=', True), 
                                    ('product_tmpl_id.secret_name', operator, value)
                        ]
                        continue
                new_domain.append(arg)
            domain = new_domain
        return super(MrpBom, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not self.env['ir.rule']._has_secret_product_groups():
            args = args or []
            domain = [
                '|',
                    '&',
                        ('product_tmpl_id.is_secret_product', '=', True),
                        ('product_tmpl_id.secret_name', operator, name),
                    '&',
                        ('product_tmpl_id.is_secret_product', '=', False),
                        '|', '|',
                            ('code', operator, name),
                            ('product_tmpl_id', operator, name),
                            ('product_id', operator, name)
            ]
            args = expression.AND([args, domain])
        return super(MrpBom, self).name_search(name=name, args=args, operator=operator, limit=limit)

    def name_get(self):
        result = super(MrpBom, self).name_get()
        if self.env['ir.rule']._has_secret_product_groups():
            return result
        result = dict(result)
        new_result = []
        for record in self:
            record_id = record.id
            product_tmpl_id = record.product_tmpl_id

            if product_tmpl_id.is_secret_product:
                record_name = product_tmpl_id.secret_name
            else:
                record_name = result[record_id]
                
            new_result.append((record_id, record_name))
        return new_result

    def _register_hook(self):
        self._cr.execute("""SELECT name, model FROM ir_model_fields WHERE ttype = 'many2one' 
        AND store is True AND relation = 'mrp.bom'""")
        domains = {}
        for field in self._cr.dictfetchall():
            field_relation = '%s.is_secret_bom' % field['name']
            domain = ['|', (field['name'], '=', False), (field_relation,'=', False)]
            domains[field['model']] = expression.AND([domains.get(field['model'], []), domain])
        self.env['ir.config_parameter'].sudo().set_param('bom.secret.domain', json.dumps(domains, default=str))
        return super(MrpBom, self)._register_hook()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    secret_name = fields.Char(string='Secret Name', translate=True)
    is_secret_product = fields.Boolean(string='Secret Product')

    def _register_hook(self):
        self._cr.execute("""SELECT name, model FROM ir_model_fields WHERE ttype = 'many2one'
        AND store is True AND relation in ('product.template', 'product.product')""")
        domains = {}
        for field in self._cr.dictfetchall():
            field_relation = '%s.is_secret_product' % field['name']
            domain = ['|', (field['name'], '=', False), (field_relation,'=', False)]
            domains[field['model']] = expression.AND([domains.get(field['model'], []), domain])
        self.env['ir.config_parameter'].sudo().set_param('product.secret.domain', json.dumps(domains, default=str))
        return super(ProductTemplate, self)._register_hook()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super(ProductTemplate, self).fields_get(allfields=allfields, attributes=attributes)
        secret_fields = ['is_secret_product', 'secret_name']
        if not any(secret_field in result for secret_field in secret_fields):
            return result
        user_secret_product = self.env['ir.rule']._has_secret_product_groups()
        user_secret_manager = self.env.user.has_group('equip3_manuf_inventory.group_mrp_secret_manager')
        for secret_field in secret_fields:
            if secret_field not in result:
                continue
            if not user_secret_product:
                result[secret_field]['searchable'] = False
                result[secret_field]['sortable'] = False
            if not user_secret_manager:
                result[secret_field]['readonly'] = True
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if not self.env['ir.rule']._has_secret_product_groups():
            domain = domain or []
            new_domain = []
            for arg in domain:
                if isinstance(arg, list) or isinstance(arg, tuple):
                    field, operator, value = arg
                    if field == self._rec_name:
                        new_domain += [
                            '|', 
                                '&', 
                                    ('is_secret_product', '=', False), 
                                    (field, operator, value),
                                '&',
                                    ('is_secret_product', '=', True), 
                                    ('secret_name', operator, value)
                        ]
                        continue
                new_domain.append(arg)
            domain = new_domain
        return super(ProductTemplate, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not self.env['ir.rule']._has_secret_product_groups():
            args = args or []
            domain = [
                '|',
                    '&',
                        ('is_secret_product', '=', True),
                        ('secret_name', operator, name),
                    '&',
                        ('is_secret_product', '=', False),
                        (self._rec_name, operator, name),
            ]
            args = expression.AND([args, domain])
        return super(ProductTemplate, self).name_search(name=name, args=args, operator=operator, limit=limit)

    def name_get(self):
        result = super(ProductTemplate, self).name_get()
        if self.env['ir.rule']._has_secret_product_groups():
            return result
        result = dict(result)
        new_result = []
        for record in self:
            name = result[record.id]
            if record.is_secret_product:
                name = record.secret_name
            new_result.append((record.id, name))
        return new_result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def search_is_secret_products(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operations not supported!'))
        return [('product_tmpl_id.is_secret_product', operator, value)]

    is_secret_product = fields.Boolean(related='product_tmpl_id.is_secret_product', search=search_is_secret_products)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if not self.env['ir.rule']._has_secret_product_groups():
            domain = domain or []
            new_domain = []
            for arg in domain:
                if isinstance(arg, list) or isinstance(arg, tuple):
                    field, operator, value = arg
                    if field == self._rec_name:
                        new_domain += [
                            '|', 
                                '&', 
                                    ('product_tmpl_id.is_secret_product', '=', False), 
                                    (field, operator, value),
                                '&',
                                    ('product_tmpl_id.is_secret_product', '=', True), 
                                    ('product_tmpl_id.secret_name', operator, value)
                        ]
                        continue
                new_domain.append(arg)
            domain = new_domain
        return super(ProductProduct, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not self.env['ir.rule']._has_secret_product_groups():
            args = args or []
            domain = [
                '|',
                    '&',
                        ('product_tmpl_id.is_secret_product', '=', True),
                        ('product_tmpl_id.secret_name', operator, name),
                    '&',
                        ('product_tmpl_id.is_secret_product', '=', False),
                        (self._rec_name, operator, name),
            ]
            args = expression.AND([args, domain])
        return super(ProductProduct, self).name_search(name=name, args=args, operator=operator, limit=limit)

    def name_get(self):
        result = super(ProductProduct, self).name_get()
        if self.env['ir.rule']._has_secret_product_groups():
            return result
        result = dict(result)
        new_result = []
        for record in self:
            name = result[record.id]
            if record.product_tmpl_id.is_secret_product:
                name = record.product_tmpl_id.secret_name
            new_result.append((record.id, name))
        return new_result


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _use_secret_product(self):
        return self.env.user.has_group('equip3_manuf_inventory.group_use_secret_product')

    def _use_secret_bom(self):
        return self.env.user.has_group('equip3_manuf_inventory.group_use_secret_bom')

    def _has_secret_product_groups(self):
        if not self._use_secret_product() or self.env.su:
            return True
        return self.env.user.has_group('equip3_manuf_inventory.group_mrp_secret_product')

    def _has_secret_bom_groups(self):
        if not self._use_secret_bom() or self.env.su:
            return True
        return self.env.user.has_group('equip3_manuf_inventory.group_mrp_secret_bom')
    
    def _has_secret_groups(self):
        has_secret_product_group = self._has_secret_product_groups()
        if has_secret_product_group:
            return True
        return self._has_secret_bom_groups()

    @api.model
    def get_secret_product_domain(self, model_name):
        if model_name in ('product.product', 'product.template'):
            return [('is_secret_product', '=', False)]
        domains = json.loads(self.env['ir.config_parameter'].sudo().get_param('product.secret.domain', '{}'))
        return domains.get(model_name, [])

    @api.model
    def get_secret_bom_domain(self, model_name):
        if model_name == 'mrp.bom':
            return [('is_secret_bom', '=', False)]
        domains = json.loads(self.env['ir.config_parameter'].sudo().get_param('bom.secret.domain', '{}'))
        return domains.get(model_name, [])

    @api.model
    def get_secret_model_domain(self, model_name):
        domain = []
        if not self._has_secret_bom_groups():
            if not self._has_secret_product_groups():
                domain = self.get_secret_product_domain(model_name)
            domain = expression.AND([domain, self.get_secret_bom_domain(model_name)])
        return domain

    @api.model
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode',
                       'tuple(self._compute_domain_context_values())'),
    )
    def _compute_domain(self, model_name, mode="read"):
        domain = super(IrRule, self)._compute_domain(model_name, mode=mode)
        if self._has_secret_groups() or model_name.startswith('ir.'):
            return domain
        secret_domain = self.get_secret_model_domain(model_name)
        return expression.AND([domain, secret_domain])
