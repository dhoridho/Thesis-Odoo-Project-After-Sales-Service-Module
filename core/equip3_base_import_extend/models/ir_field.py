from odoo import models,api
REFERENCING_FIELDS = {None, 'id', '.id'}
def only_ref_fields(record):
    return {k: v for k, v in record.items() if k in REFERENCING_FIELDS}
def exclude_ref_fields(record):
    return {k: v for k, v in record.items() if k not in REFERENCING_FIELDS}

class Equip3IrFieldsConverter(models.AbstractModel):
    _inherit = 'ir.fields.converter'
    
    
    @api.model
    def for_model_2(self, model, fromtype=str):
        """ Returns a converter object for the model. A converter is a
        callable taking a record-ish (a dictionary representing an odoo
        record with values of typetag ``fromtype``) and returning a converted
        records matching what :meth:`odoo.osv.orm.Model.write` expects.

        :param model: :class:`odoo.osv.orm.Model` for the conversion base
        :returns: a converter callable
        :rtype: (record: dict, logger: (field, error) -> None) -> dict
        """
        # make sure model is new api
        model = self.env[model._name]

        converters = {
            name: self.to_field(model, field, fromtype)
            for name, field in model._fields.items()
        }

        def fn(record, log):
            converted = {}
            for field, value in record.items():
                if field in REFERENCING_FIELDS:
                    continue
                if not value:
                    converted[field] = False
                    continue
                try:
                    converted[field], ws = converters[field](value)
                    for w in ws:
                        if isinstance(w, str):
                            # wrap warning string in an ImportWarning for
                            # uniform handling
                            w = ImportWarning(w)
                        log(field, w)
                except ValueError as e:
                    log(field, e)
                    converted['_import_skip_create'] = True
            return converted

        return fn