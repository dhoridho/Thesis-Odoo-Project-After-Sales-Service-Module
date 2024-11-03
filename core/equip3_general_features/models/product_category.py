import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def create(self, vals):
        if vals.get('is_generate_product_code') and not vals.get('category_prefix'):
            vals['category_prefix'] = self._prefix_from_name(vals.get('name'))
        return super(ProductCategory, self).create(vals)

    is_generate_product_code = fields.Boolean(string="Autogenerate Product Code", default=True)
    category_prefix_preference = fields.Selection([
        ('all_products_in_this_category_will_have_same_prefix' , 'All Products In This Category Will Have Same Prefix'),
        ('each_product_will_have_different_prefix' , 'Additional Prefix Will Be Define On Product'),
        ], string="Prefix Preference", default='all_products_in_this_category_will_have_same_prefix')
    category_prefix = fields.Char(string="Product Category Prefix")
    digits = fields.Integer(string="Digits", default=3)
    current_sequence = fields.Char(string="Current Sequence", default='001')
    separator = fields.Char(string="Separator", default='-')

    @api.constrains('category_prefix')
    def _check_prefix_limit(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        prefix_limit = int(IrConfigParam.get_param('prefix_limit', 5))
        for record in self.filtered(lambda o: o.is_generate_product_code):
            if len(record.category_prefix) > prefix_limit:
                raise ValidationError("Prefix value size must be less or equal to %s" % (prefix_limit))

    @api.constrains('digits')
    def _check_digits(self):
        for record in self.filtered(lambda o: o.is_generate_product_code):
            if record.digits < 1:
                raise ValidationError(_('Digits must be positive!'))

    @api.constrains('current_sequence')
    def _check_current_sequence(self):
        for record in self.filtered(lambda o: o.is_generate_product_code):
            if not record.current_sequence.isnumeric():
                raise ValidationError(_('Sequence must be numeric!'))

    @api.constrains('digits', 'current_sequence')
    def _check_digits_consistency(self):
        for record in self.filtered(lambda o: o.is_generate_product_code):
            if record.digits != len(record.current_sequence) and len(str(int(record.current_sequence))) <= record.digits:
                raise ValidationError(_('The length of sequence (%s) is %s while digits is %s!' % (record.current_sequence, len(record.current_sequence), record.digits)))

    @api.onchange('digits')
    def _onchange_digits(self):
        if self.digits > 1:
            self.current_sequence = str(int(self.current_sequence)).zfill(self.digits)

    @api.model
    def _prefix_from_name(self, name):
        if not name:
            return False
        split_name = name.strip().split()
        if len(split_name) == 1:
            return split_name[0][:3].upper()
        elif len(split_name) == 2:
            name = split_name[0][0]
            name_1 = split_name[1][0]
            name_2 = ''
            if len(split_name[1]) > 1:
                name_2 = split_name[1][1]
            return (name + name_1 + name_2).upper()
        elif len(split_name) > 2:
            name = split_name[0][0]
            name_1 = split_name[1][0]
            name_2 = split_name[2][0]
            return (name + name_1 + name_2).upper()
        return False

    @api.onchange('name')
    def _onchange_name(self):
        self.category_prefix = self._prefix_from_name(self.name)

    def _next_sequence(self, product_prefix, product_id=None):
        if not self:
            return False
        
        self.ensure_one()
        if not self.is_generate_product_code:
            return False

        prefix_preference = self.category_prefix_preference
        categ_prefix = self.category_prefix
        separator = self.separator

        where = []
        query_params = []
        if product_id:
            where += ['pt.id != %s']
            query_params += [product_id]
        where += ['pt.default_code = %s']
        where = ' AND '.join(where)

        query = """
        SELECT
            pt.id
        FROM
            product_template pt
        WHERE
            {where}
        """.format(where=where)

        number = int(self.current_sequence)
        while True:
            next_number = str(number).zfill(self.digits)
            if prefix_preference == 'each_product_will_have_different_prefix':
                default_code = [categ_prefix, product_prefix, next_number]
            else:
                default_code = [categ_prefix, next_number]
            default_code = separator.join([o for o in default_code if o])

            self._cr.execute(query, query_params + [default_code])
            result = self._cr.fetchone()
            if not result:
                return default_code
            number += 1

    def _check_and_update_next_sequence(self, default_code):
        self.ensure_one()
        if self.separator not in default_code:
            _logger.info(_("Product code (%s) doesn't contains separator (%s)" % (default_code, self.separator)))

        current_sequence = default_code.split('-')[-1]
        if not current_sequence.isnumeric():
            raise ValidationError(_("Cannot determine next sequence from product code (%s)" % (default_code,)))

        next_sequence = str(int(current_sequence) + 1).zfill(self.digits)
        self.write({'current_sequence': next_sequence})
