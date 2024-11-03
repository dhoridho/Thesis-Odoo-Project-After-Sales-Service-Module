import logging
from odoo.fields import Many2one, prefetch_many2one_ids
from odoo.tools import IterableGenerator

_logger = logging.getLogger(__name__)


class Many2oneCustomUoM(Many2one):

    product_field = 'product_id'

    def product_context(self, record):
        if record._name in ('product.product', 'product.template'):
            product = record
        else:
            try:
                product = record[self.product_field]
            except Exception as err:
                _logger.warning('Custom UoM: %s (%s)' % (err, self.model_name))
                product = record.env['product.product']
        return {'product_field': product}

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        ids = () if value is None else (value,)
        prefetch_ids = IterableGenerator(prefetch_many2one_ids, record, self)
        context = record.env.context.copy()
        if self.comodel_name == 'uom.uom':
            context.update(self.product_context(record))
        return record.pool[self.comodel_name]._browse(record.env(context=context), ids, prefetch_ids)


Many2one.product_field = Many2oneCustomUoM.product_field
Many2one.product_context = Many2oneCustomUoM.product_context
Many2one.convert_to_record = Many2oneCustomUoM.convert_to_record
