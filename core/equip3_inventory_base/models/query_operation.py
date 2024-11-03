import logging
from odoo import models, fields, api, _
from odoo.addons.base.models.ir_model import quote
from collections import defaultdict
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QueryOperation(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _query_create_default_values(self):
        now = fields.Datetime.now()
        user = self.env.user

        return {
            'create_date': now,
            'write_date': now,
            'create_uid': user.id,
            'write_uid': user.id
        }

    @api.model
    def _get_query_create(self, vals_list):
        model = self._name
        model_fields = self.env[model]._fields
        default_values = self.env[model]._query_create_default_values()

        field_list = []
        for field_name in default_values.keys():
            if field_name not in field_list:
                field_list += [field_name]

        for vals in vals_list:
            for field_name in vals.keys():
                if field_name not in field_list:
                    field_list += [field_name]

        direct_field_list = []
        o2m_fields = []
        m2m_fields = []
        for field_name in field_list:
            field = model_fields[field_name]
            if field.type == 'one2many':
                o2m_fields += [field]
            elif field.type == 'many2many':
                m2m_fields += [field]
            else:
                direct_field_list += [field]

        records = []
        o2m_field_values = defaultdict(lambda: defaultdict(lambda: []))
        m2m_field_values = defaultdict(lambda: defaultdict(lambda: []))
        for parent_index, vals in enumerate(vals_list):
            tmp_vals = default_values.copy()
            tmp_vals.update(vals)

            record = []
            for field in direct_field_list:
                if field.type in ('float', 'integer', 'monetary'):
                    value = tmp_vals.get(field.name, 0.0)
                elif field.type == 'many2one':
                    value = tmp_vals.get(field.name) or None
                else:
                    value = tmp_vals.get(field.name)
                record += [value]

            records += [record]

            for o2m_field in o2m_fields:
                try:
                    o2m_vals_list = tmp_vals.pop(o2m_field.name)
                except KeyError:
                    o2m_vals_list = []
                
                for o2m_vals in o2m_vals_list:
                    o2m_code, *anything = o2m_vals
                    o2m_field_values[o2m_code][o2m_field] += [(o2m_vals, parent_index)]

            for m2m_field in m2m_fields:
                try:
                    m2m_vals_list = tmp_vals.pop(m2m_field.name)
                except KeyError:
                    m2m_vals_list = []

                for m2m_vals in m2m_vals_list:
                    m2m_code, *anything = m2m_vals
                    m2m_field_values[m2m_code][m2m_field] += [(m2m_vals, parent_index)]

        return direct_field_list, records, o2m_field_values, m2m_field_values

    @api.model
    def _query_create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        model_name = self._name

        if not vals_list:
            return self.env[model_name].browse()
        
        table = self.env[model_name]._table

        direct_field_list, records, o2m_values, m2m_values = self._get_query_create(vals_list)
        query = "INSERT INTO {table} ({cols}) VALUES %s RETURNING id".format(
            table=table,
            cols=', '.join(quote(field.name) for field in direct_field_list))
        row = "({this})".format(this=', '.join("%s" for o in direct_field_list))

        query_vals = ', '.join(self.env.cr.mogrify(row, tuple(record)).decode('utf-8') for record in records)

        self._query_execute(query % query_vals)
        record_ids_dict = {index: record[0] for index, record in enumerate(self.env.cr.fetchall())}

        for o2m_code, o2m_fields in o2m_values.items():
            if o2m_code == 0:
                for o2m_field, o2m_vals_list in o2m_fields.items():
                    new_o2m_vals_list = []
                    for o2m_vals, parent_index in o2m_vals_list:
                        o2m_vals[-1][o2m_field.inverse_name] = record_ids_dict[parent_index]
                        new_o2m_vals_list += [o2m_vals[-1].copy()]
                    self.env[o2m_field.comodel_name]._query_create(new_o2m_vals_list)
            
            elif o2m_code == 6:
                for o2m_field, o2m_vals_list in o2m_fields.items():
                    for o2m_vals, parent_index in o2m_vals_list:
                        parent_id = record_ids_dict[parent_index]

                        query = "UPDATE {table} SET {inverse} = NULL WHERE {inverse} = {parent}".format(
                            table=self.env[o2m_field.comodel_name]._table,
                            inverse=o2m_field.inverse_name,
                            parent=parent_id)
                        self._query_execute(query)

                        to_assign_ids = o2m_vals[-1]
                        if not to_assign_ids:
                            continue

                        query = "UPDATE {table} SET {inverse} = {parent} WHERE id IN %s".format(
                            table=self.env[o2m_field.comodel_name]._table,
                            inverse=o2m_field.inverse_name,
                            parent=parent_id)
                        self._query_execute(query, [tuple(to_assign_ids)])

        for m2m_code, m2m_fields in m2m_values.items():
            if m2m_code == 6:
                for m2m_field, m2m_vals_list in m2m_fields.items():

                    to_unlink = []
                    to_link = []
                    for m2m_vals, parent_index in m2m_vals_list:
                        parent_id = record_ids_dict[parent_index]
                        to_unlink += [parent_id]
                        to_link += [(parent_id, item_id) for item_id in m2m_vals[-1]]

                    if to_unlink:
                        self._query_execute("DELETE FROM {table} WHERE {column1} IN %s".format(
                            table=m2m_field.relation,
                            column1=m2m_field.column1
                        ), [tuple(to_unlink)])

                    if to_link:
                        query = "INSERT INTO {table} ({cols}) VALUES %s".format(
                            table=m2m_field.relation,
                            cols=', '.join(quote(field_name) for field_name in (m2m_field.column1, m2m_field.column2)))
                        row = "({this})".format(this=', '.join("%s" for o in (m2m_field.column1, m2m_field.column2)))
                        query_vals = ', '.join(self.env.cr.mogrify(row, tuple(record)).decode('utf-8') for record in to_link)
                        self._query_execute(query % query_vals)

        records = self.env[model_name].browse(record_ids_dict.values())
        records.invalidate_cache()
        return records

    def _query_execute(self, query, params=None):
        if not params:
            self.env.cr.execute(query)
        else:
            self.env.cr.execute(query, params)
