import logging
import functools
from odoo import models, api
from odoo.tools.view_validation import get_domain_identifiers
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def user_has_groups(self, groups):
        """Return true if the user is member of at least one of the groups in
        ``groups``, and is not a member of any of the groups in ``groups``
        preceded by ``!``. Typically used to resolve ``groups`` attribute in
        view and model definitions.

        :param str groups: comma-separated list of fully-qualified group
            external IDs, e.g., ``base.group_user,base.group_system``,
            optionally preceded by ``!``
        :return: True if the current user is a member of one of the given groups
            not preceded by ``!`` and is not member of any of the groups
            preceded by ``!``
        """
        from odoo.http import request
        user = self.env.user

        has_groups = []
        not_has_groups = []
        for group_ext_id in groups.split(','):
            group_ext_id = group_ext_id.strip()
            if group_ext_id[0] == '!':
                not_has_groups.append(group_ext_id[1:])
            else:
                has_groups.append(group_ext_id)

        for group_ext_id in not_has_groups:
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if user.has_group(group_ext_id) and request and request.session.debug:
                    return False
            else:
                if group_ext_id.isnumeric():
                    group = self.env['res.groups'].browse(int(group_ext_id))
                    if user in group.users:
                        return False
                else:
                    if user.has_group(group_ext_id):
                        return False

        for group_ext_id in has_groups:
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if user.has_group(group_ext_id) and request and request.session.debug:
                    return True
            else:
                if group_ext_id.isnumeric():
                    group = self.env['res.groups'].browse(int(group_ext_id))
                    if user in group.users:
                        return True
                else:
                    if user.has_group(group_ext_id):
                        return True

        return not has_groups

    @api.model
    def check_field_access_rights(self, operation, fields):
        return fields or list(self._fields)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ fields_get([fields][, attributes])

        Return the definition of each field.

        The returned value is a dictionary (indexed by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param allfields: list of fields to document, all if empty or not provided
        :param attributes: list of description attributes to return for each field, all if empty or not provided
        """
        has_access = functools.partial(self.check_access_rights, raise_exception=False)
        readonly = not (has_access('write') or has_access('create'))

        res = {}
        for fname, field in self._fields.items():
            if allfields and fname not in allfields:
                continue

            description = field.get_description(self.env)
            if field.groups and not self.env.su and not self.user_has_groups(field.groups):
                description['searchable'] = False
                description['sortable'] = False

            if readonly:
                description['readonly'] = True
                description['states'] = {}
            if attributes:
                description = {key: val
                               for key, val in description.items()
                               if key in attributes}
            res[fname] = description

        return res
    
    def read(self, fields=None, load='_classic_read'):
        """ read([fields])

        Reads the requested fields for the records in ``self``, low-level/RPC
        method. In Python code, prefer :meth:`~.browse`.

        :param fields: list of field names to return (default is all fields)
        :return: a list of dictionaries mapping field names to their values,
                 with one dictionary per record
        :raise AccessError: if user has no read rights on some of the given
                records
        """
        fields = self.check_field_access_rights('read', fields)

        # fetch stored fields from the database to the cache
        stored_fields = set()
        for name in fields:
            field = self._fields.get(name)
            if not field:
                raise ValueError("Invalid field %r on model %r" % (name, self._name))
            if field.store:
                stored_fields.add(name)
            elif field.compute:
                # optimization: prefetch direct field dependencies
                for dotname in field.depends:
                    f = self._fields[dotname.split('.')[0]]
                    if f.prefetch:
                        stored_fields.add(f.name)
        self._read(stored_fields)

        return self._read_format(fnames=fields, load=load)

    def _fetch_field(self, field):
        """ Read from the database in order to fetch ``field`` (:class:`Field`
            instance) for ``self`` in cache.
        """
        self.check_field_access_rights('read', [field.name])
        # determine which fields can be prefetched
        if self._context.get('prefetch_fields', True) and field.prefetch:
            fnames = [
                name
                for name, f in self._fields.items()
                # select fields that can be prefetched
                if f.prefetch
                # discard fields that must be recomputed
                if not (f.compute and self.env.records_to_compute(f))
            ]
            if field.name not in fnames:
                fnames.append(field.name)
                self = self - self.env.records_to_compute(field)
        else:
            fnames = [field.name]
        self._read(fnames)

    def _filter_valid_context(self, context):
        
        def _is_valid(field_name):
            try:
                field = self._fields[field_name.split(':')[0]]
                if field.groups and not self.user_has_groups(groups=field.groups):
                    return False
            except Exception as err:
                _logger.info(str(err))
            return True

        if isinstance(context, str):
            context = safe_eval.safe_eval(context, {'context': self._context})

        for ctx in ['group_by', 'pivot_measures', 'pivot_column_groupby', 'pivot_row_groupby']:
            if ctx in context and isinstance(context[ctx], list):
                context[ctx] = [fname for fname in context[ctx] if _is_valid(fname)]
        return context

    @api.model
    def load_views(self, views, options=None):
        result = super(BaseModel, self).load_views(views, options)
        for flt in result.get('filters', []):
            if 'context' in flt:
                flt['context'] = self._filter_valid_context(flt['context'])
        return result
