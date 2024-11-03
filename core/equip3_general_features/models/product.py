import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from re import findall as regex_findall
from re import split as regex_split

_logger = logging.getLogger(__name__)

class StockProduct(models.Model):
    _inherit = 'product.template'

    multi_companies_all = fields.Many2many('res.company', 'product_id', 'company_id', 'prod_comp_id', string='Allowed  Companies', tracking=True)
    product_brand_id = fields.Many2one('product.brand', string='Brand')
    alternative_product_ids = fields.Many2many('product.product', 'product_product_alternative_rel', 'product_id', 'tmpl_id', string="Alternative Product")    
    default_code = fields.Char(string="Product Code", compute='_compute_default_code', inverse='_set_default_code', required=False)
    product_prefix = fields.Char(string="Product Code Prefix", required=False, size=10)
     # categ_id related fields
    is_generate_product = fields.Boolean(related='categ_id.is_generate_product_code')
    category_prefix_preference = fields.Selection(related='categ_id.category_prefix_preference')
    category_sequence = fields.Char(string='Category Sequence', related='categ_id.current_sequence')
    is_invisible_standard_price = fields.Boolean(compute='_compute_attrs_standard_price')
    is_readonly_standard_price = fields.Boolean(compute='_compute_attrs_standard_price')

    @api.model
    def get_import_templates(self):
        return [{
                    'label': _('Import Template for Products'),
                    'template': '/equip3_general_features/static/xls/product_template.xls'
                }]

    @api.constrains('default_code')
    def _check_constrain_default_code(self):
        for record in self.filtered(lambda o: o.default_code):
            template = self.env['product.template'].search([
                ('default_code', '=', record.default_code),
                ('id', '!=', record.id)
            ], limit=1)
            if template:
                raise ValidationError(_('Product Code must be unique.'))

    @api.depends('product_variant_ids', 'product_variant_ids.default_code', 'categ_id', 'product_prefix')
    def _compute_default_code(self):
        if not any(self.ids):
            # onchange
            for template in self:
                template_id = template.id
                if isinstance(template, models.NewId):
                    template_id = None

                categ = template.categ_id
                default_code = False
                if categ.is_generate_product_code:
                    default_code = categ._next_sequence(template.product_prefix, product_id=template_id)
                template.default_code = default_code
        else:
            # compute
            for template in self:
                categ = template.categ_id
                separator = categ.separator or '-'
                prefix_preference = categ.category_prefix_preference

                variants = template.product_variant_ids
                if variants:
                    variant_default_code = variants[0].default_code or ''
                    default_codes = variant_default_code.split(separator)
                    try:
                        categ_prefix, *prefix, categ_number = default_codes
                        if prefix_preference == 'each_product_will_have_different_prefix':
                            default_code = separator.join(o for o in (categ_prefix, template.product_prefix, categ_number) if o)
                        else:
                            default_code = separator.join(o for o in (categ_prefix, categ_number) if o)
                    except ValueError:
                        default_code = categ._next_sequence(template.product_prefix, product_id=template.id)
                else:
                    default_code = False

                template.default_code = default_code

    def _set_default_code(self):
        for template in self:
            template.product_variant_ids.default_code = template.default_code

    @api.depends('cost_method')
    def _compute_attrs_standard_price(self):
        for record in self:
            record.is_invisible_standard_price = record._is_invisible_standard_price()
            record.is_readonly_standard_price = record._is_readonly_standard_price()

    def _is_invisible_standard_price(self):
        self.ensure_one()
        return False

    def _is_readonly_standard_price(self):
        self.ensure_one()
        return self.cost_method != 'standard'     

    def _update_categ_sequence(self):
        self.ensure_one()
        try:
            default_code = regex_findall(r'\d+', self.default_code)
            if default_code:
                default_code = default_code[-1]
                if int(default_code) > int(categ.current_sequence):
                    self.categ_id.current_sequence = str(int(default_code) + 1).zfill(categ.digits)
        except Exception as e:
            pass

    @api.onchange('name', 'categ_id')
    def _onchange_categ_set_product_prefix(self):
        categ = self.categ_id
        if categ.is_generate_product_code and categ.category_prefix_preference == 'each_product_will_have_different_prefix':
            self.product_prefix = categ._prefix_from_name(self.name)

    @api.constrains('categ_id', 'product_prefix')
    def _check_categ_with_different_prefix(self):
        for template in self.filtered(lambda o: o.categ_id.is_generate_product_code and o.categ_id.category_prefix_preference == 'each_product_will_have_different_prefix'):
            if not template.product_prefix:
                raise ValidationError(_("Product Prefix (product_prefix) is required while product category prefix preferenece is 'Additional Prefix Will Be Define On Product'!"))

    @api.model
    def create(self, vals):
        if vals.get('categ_id', False):
            categ = self.env['product.category'].browse(vals['categ_id'])
            if categ.is_generate_product_code:
                if categ.category_prefix_preference == 'each_product_will_have_different_prefix' and not vals.get('product_prefix'):
                    vals['product_prefix'] = categ._prefix_from_name(vals.get('name'))
        return super(StockProduct, self).create(vals)

    @api.model
    def _repair_default_code(self):
        self._cr.execute("""
        SELECT
            pc.id
        FROM
            product_category pc
        WHERE
            pc.is_generate_product_code IS True
        """)
        auto_categories = self.env['product.category'].browse([o[0] for o in self._cr.fetchall()]).sudo()
        _logger.info('Checking & repairing %s product.category!' % (len(auto_categories),))
        
        for category in auto_categories:
            values = {}
            if not category.category_prefix_preference:
                values['category_prefix_preference'] = 'all_products_in_this_category_will_have_same_prefix'
            if not category.category_prefix:
                values['category_prefix'] = category._prefix_from_name(category.name)
            if not category.digits:
                values['digits'] = 3
            if not category.separator:
                values['separator'] = '-'

            digits = values.get('digits', category.digits)
            if not category.current_sequence:
                values['current_sequence'] = '1'.zfill(digits)
            elif digits != len(category.current_sequence):
                if category.current_sequence.isnumeric():
                    values['current_sequence'] = str(int(category.current_sequence)).zfill(digits)
                else:
                    values['current_sequence'] = '1'.zfill(digits)
            if values:
                category.with_context(tracking_disable=True).write(values)

        self._cr.execute("""
        SELECT
            pt.id
        FROM
            product_template pt
        LEFT JOIN
            product_category pc
            ON (pc.id = pt.categ_id)
        WHERE
            pc.is_generate_product_code IS True AND
            pc.category_prefix_preference = 'each_product_will_have_different_prefix' AND
            (pt.product_prefix IS NULL OR COALESCE(TRIM(pt.product_prefix), '') = '')
        """)
        no_product_prefix = self.browse([o[0] for o in self._cr.fetchall()]).sudo()
        _logger.info('Repairing %s product.template without product_prefix!' % (len(no_product_prefix),))

        for template in no_product_prefix:
            categ = template.categ_id
            template.with_context(tracking_disable=True).product_prefix = categ._prefix_from_name(template.name)

        self._cr.execute("""
        SELECT
            pt.id
        FROM
            product_template pt
        WHERE
            pt.default_code IS NULL OR
            COALESCE(TRIM(pt.default_code), '=') = ''
        """)
        no_default_code = self.browse([o[0] for o in self._cr.fetchall()]).sudo()

        self._cr.execute("""
        SELECT
            pp.product_tmpl_id
        FROM
            product_product pp
        WHERE
            pp.default_code IS NULL OR
            COALESCE(TRIM(pp.default_code), '=') = ''
        """)
        no_default_code |= self.browse([o[0] for o in self._cr.fetchall()]).sudo()
        _logger.info('Repairing %s product without default_code' % (len(no_default_code),))

        for template in no_default_code:
            categ = template.categ_id
            if categ.is_generate_product_code:
                default_code = categ._next_sequence(template.product_prefix, product_id=template.id)
                categ._check_and_update_next_sequence(default_code)
            else:
                default_code = 'DEFCODE'
                next_default_code = default_code
                number = 1
                while self.search([
                    ('default_code', '=', next_default_code),
                    ('id', '!=', template.id)
                ], limit=1):
                    next_default_code = '%s%s' % (default_code, number)
                    number += 1
                default_code = next_default_code
            template.with_context(tracking_disable=True).default_code = default_code   

class ProductProduct(models.Model):
    _inherit = 'product.product'

    alternative_product_ids = fields.Many2many('product.product', 'prod_id_alternative_rel', 'prod', 'prod_id', string="Alternative Product")    

    is_invisible_standard_price = fields.Boolean(compute='_compute_attrs_standard_price')
    is_readonly_standard_price = fields.Boolean(compute='_compute_attrs_standard_price')

    @api.depends('cost_method')
    def _compute_attrs_standard_price(self):
        for record in self:
            record.is_invisible_standard_price = record._is_invisible_standard_price()
            record.is_readonly_standard_price = record._is_readonly_standard_price()

    def _is_invisible_standard_price(self):
        self.ensure_one()
        return False

    def _is_readonly_standard_price(self):
        self.ensure_one()
        return self.cost_method != 'standard'


class InheritProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    minimum_price = fields.Float(string='Min Price')
    maximum_price = fields.Float(string='Max Price')
