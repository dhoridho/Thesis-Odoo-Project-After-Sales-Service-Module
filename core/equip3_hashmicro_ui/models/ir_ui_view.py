import os
import logging
import collections

from odoo import models, api, tools, _
from lxml import etree
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

_validators = collections.defaultdict(list)
_relaxng_cache = {}


def valid_view(arch, **kwargs):
    for pred in _validators[arch.tag]:
        check = pred(arch, **kwargs)
        if not check:
            _logger.error("Invalid XML: %s", pred.__doc__)
            return False
        if check == "Warning":
            _logger.warning("Invalid XML: %s", pred.__doc__)
            return "Warning"
    return True


def validate(*view_types):
    """ Registers a view-validation function for the specific view types
    """
    def decorator(fn):
        for arch in view_types:
            _validators[arch].append(fn)
        return fn
    return decorator


def relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type != 'tree':
        path = os.path.join('base', 'rng', '%s_view.rng' % view_type)
    else:
        path = os.path.join('equip3_hashmicro_ui', 'rng', 'tree_view.rng')
    if view_type not in _relaxng_cache or view_type == 'tree':
        with tools.file_open(path) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


@validate('calendar', 'graph', 'pivot', 'search', 'tree', 'activity')
def schema_valid(arch, **kwargs):
    """ Get RNG validator and validate RNG file."""
    validator = relaxng(arch.tag)
    if validator and not validator.validate(arch):
        result = True
        for error in validator.error_log:
            _logger.error(tools.ustr(error))
            result = False
        return result
    return True


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.constrains('arch_db')
    def _check_xml(self):
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        for view in self:
            try:
                view_arch = etree.fromstring(view.arch.encode('utf-8'))
                view._valid_inheritance(view_arch)
                view_def = view.read_combined(['arch'])
                view_arch_utf8 = view_def['arch']
                if view.type == 'qweb':
                    continue
                view_doc = etree.fromstring(view_arch_utf8)
                # verify that all fields used are valid, etc.
                view.postprocess_and_fields(view_doc, validate=True)
                # RNG-based validation is not possible anymore with 7.0 forms
                view_docs = [view_doc]
                if view_docs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    view_docs = view_docs[0]
                for view_arch in view_docs:
                    check = valid_view(view_arch, env=self.env, model=view.model)
                    view_name = ('%s (%s)' % (view.name, view.xml_id)) if view.xml_id else view.name
                    if not check:
                        raise ValidationError(_(
                            'Invalid view %(name)s definition in %(file)s',
                            name=view_name, file=view.arch_fs
                        ))
                    if check == "Warning":
                        _logger.warning('Invalid view %s definition in %s \n%s', view_name, view.arch_fs, view.arch)
            except ValueError as e:
                raise ValidationError(_(
                    "Error while validating view:\n\n%(error)s",
                    error=tools.ustr(e),
                )).with_traceback(e.__traceback__) from None

        return True
