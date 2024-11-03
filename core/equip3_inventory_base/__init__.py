from . import models
from . import wizard

from odoo.addons.stock_account.models.product import ProductCategory as BasicProductCategory
import logging

_logger = logging.getLogger(__name__)

def uninstall_hook(cr, registry):
    try:
        BasicProductCategory._revert_method('write')
    except Exception as err:
        _logger.error(str(err))
