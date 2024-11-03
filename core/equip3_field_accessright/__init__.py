from . import models

from odoo import api, fields, SUPERUSER_ID


class Field(fields.Field):

    def _setup_related_full(self, model):
        """ Setup the attributes of a related field. """
        # fix the type of self.related if necessary
        if isinstance(self.related, str):
            self.related = tuple(self.related.split('.'))

        # determine the chain of fields, and make sure they are all set up
        model_name = self.model_name
        for name in self.related:
            field = model.pool[model_name]._fields[name]
            if field._setup_done != 'full':
                field.setup_full(model.env[model_name])
            model_name = field.comodel_name

        self.related_field = field

        # check type consistency
        if self.type != field.type:
            raise TypeError("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        if self._depends is not None:
            self.depends = self._depends
        else:
            self.depends = ('.'.join(self.related),)
        self.compute = self._compute_related
        if self.inherited or not (self.readonly or field.readonly):
            self.inverse = self._inverse_related
        if field._description_searchable:
            # allow searching on self only if the related field is searchable
            self.search = self._search_related

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            if attr == 'groups':
                continue
            if not getattr(self, attr):
                setattr(self, attr, getattr(field, prop))

        for attr, value in field.__dict__.items():
            if not hasattr(self, attr) and model._valid_field_parameter(self, attr):
                setattr(self, attr, value)

        # special cases of inherited fields
        if self.inherited:
            if not self.states:
                self.states = field.states
            if field.required:
                self.required = True
            self._modules.update(field._modules)

        if self._depends_context is not None:
            self.depends_context = self._depends_context
        else:
            self.depends_context = field.depends_context


def _patch():
    setattr(fields.Field, '_setup_related_full_origin', fields.Field._setup_related_full)
    fields.Field._setup_related_full = Field._setup_related_full

def _revert(cr, registry):
    if hasattr(fields.Field, '_setup_related_full_origin'):
        fields.Field._setup_related_full = fields.Field._setup_related_full_origin
