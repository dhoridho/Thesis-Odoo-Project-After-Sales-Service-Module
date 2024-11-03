import json
import logging
from odoo import models, api, tools, fields
from odoo.tools import unique, config
from odoo.addons.base.models.ir_model import quote, mark_modified, upsert, field_xmlid

_logger = logging.getLogger(__name__)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    groups_str = fields.Char(compute='_compute_group_str')

    def _compute_group_str(self):
        for field in self:
            field.groups_str = self.env[field.model]._fields[field.name].groups

    def _register_hook(self):
        super(IrModelFields, self)._register_hook()
        group_to_assign = json.loads(self.env['ir.config_parameter'].sudo().get_param('field_group_to_assign', '[]'))
        failed_field_group_pairs = []
        for field_id, group_xml_id in group_to_assign:
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if group:
                group.field_access = [(4, field_id)]
            else:
                failed_field_group_pairs += [(field_id, group_xml_id)]
        self._dumps_field_group_to_assign(failed_field_group_pairs)
    
    @api.model
    def _dumps_field_group_to_assign(self, field_group_pairs):
        self.env['ir.config_parameter'].sudo().set_param('field_group_to_assign', json.dumps(field_group_pairs, default=str))

    def _reflect_field_params(self, field, model_id):
        params = super(IrModelFields, self)._reflect_field_params(field, model_id)
        group_ids = []
        if field.groups:
            for group_xml_id in field.groups.split(','):
                group = self.env.ref(group_xml_id, raise_if_not_found=False)
                if group:
                    group_ids += [group.id]
                else:
                    group_ids += [group_xml_id]
        params['groups'] = set(group_ids)
        return params

    def _reflect_fields(self, model_names):
        """ Reflect the fields of the given models. """
        cr = self.env.cr

        for model_name in model_names:
            model = self.env[model_name]
            by_label = {}
            for field in model._fields.values():
                if field.string in by_label:
                    _logger.warning('Two fields (%s, %s) of %s have the same label: %s.',
                                    field.name, by_label[field.string], model, field.string)
                else:
                    by_label[field.string] = field.name

        # determine expected and existing rows
        rows = []
        groups = []
        for model_name in model_names:
            model_id = self.env['ir.model']._get_id(model_name)
            for field in self.env[model_name]._fields.values():
                params = self._reflect_field_params(field, model_id)
                groups.append(params.pop('groups'))
                rows.append(params)
        cols = list(unique(['model', 'name'] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]
        expected_groups = [(row['model'], row['name'], group) for row, group in zip(rows, groups)]

        query = "SELECT {}, id FROM ir_model_fields WHERE model IN %s".format(
            ", ".join(quote(col) for col in cols),
        )
        cr.execute(query, [tuple(model_names)])
        field_ids = {}
        existing = {}
        for row in cr.fetchall():
            field_ids[row[:2]] = row[-1]
            existing[row[:2]] = row[:-1]

        query = "SELECT {}, STRING_AGG(rel.group_id::character varying, ',') AS groups FROM ir_model_fields imf LEFT JOIN ir_model_fields_group_rel rel ON (rel.field_id = imf.id) WHERE imf.model IN %s GROUP BY {}".format(
            ", ".join('imf.' + quote(col) for col in ['model', 'name']), ", ".join('imf.' + quote(col) for col in ['model', 'name'])
        )

        cr.execute(query, [tuple(model_names)])
        existing_groups = {}
        for row in cr.fetchall():
            existing_groups[row[:2]] = set([int(gid) for gid in row[2].split(',')] if row[2] else [])

        # create or update rows
        rows = [row for row in expected if existing.get(row[:2]) != row]
        if rows:
            ids = upsert(cr, self._table, cols, rows, ['model', 'name'])
            for row, id_ in zip(rows, ids):
                field_ids[row[:2]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        groups = [group for group in expected_groups if existing_groups.get(group[:2]) != group[-1]]
        if groups:
            group_field_ids = [field_ids[group[:2]] for group in groups]
            group_field_pairs = []
            group_field_pairs_xmlids = []
            for group in groups:
                field_id = field_ids[group[:2]]
                group_field_ids += [field_id]
                for group_id in list(group[-1]):
                    if isinstance(group_id, int): 
                        group_field_pairs += [(field_id, group_id)]
                    else:
                        group_field_pairs_xmlids += [(field_id, group_id)]

            query = "DELETE FROM ir_model_fields_group_rel WHERE field_id IN %s"
            cr.execute(query, [tuple(group_field_ids)])
            cr.commit()
            
            if group_field_pairs:
                query = "INSERT INTO ir_model_fields_group_rel ({cols}) VALUES {rows}".format(
                    cols=", ".join(quote(col) for col in ('field_id', 'group_id')),
                    rows=", ".join("%s" for row in group_field_pairs))

                cr.execute(query, group_field_pairs)
                cr.commit()

            if group_field_pairs_xmlids:
                group_field_pairs_xmlids += json.loads(self.env['ir.config_parameter'].sudo().get_param('field_group_to_assign', '[]'))
                self._dumps_field_group_to_assign(group_field_pairs_xmlids)

        # update their XML id
        module = self._context.get('module')
        if not module:
            return

        data_list = []
        for (field_model, field_name), field_id in field_ids.items():
            model = self.env[field_model]
            field = model._fields.get(field_name)
            if field and (
                module == model._original_module
                or module in field._modules
                or any(
                    # module introduced field on model by inheritance
                    field_name in self.env[parent]._fields
                    for parent, parent_module in model._inherit_module.items()
                    if module == parent_module
                )
            ):
                xml_id = field_xmlid(module, field_model, field_name)
                record = self.browse(field_id)
                data_list.append({'xml_id': xml_id, 'record': record})
        self.env['ir.model.data']._update_xmlids(data_list)

    def _update_field_groups(self, force=False):
        if not self.ids:
            return
        
        cr = self.env.cr
        query = """
            SELECT 
                imf.model,
                imf.name,
                STRING_AGG(rel.group_id::character varying, ',') AS groups 
            FROM 
                ir_model_fields imf
            LEFT JOIN
                ir_model_fields_group_rel rel
                ON (imf.id = rel.field_id)
            WHERE 
                imf.id IN %s 
            GROUP BY 
                imf.model, imf.name
        """
        cr.execute(query, [tuple(self.ids)])

        field_groups = {}
        all_group_ids = []
        for model, name, groups in cr.fetchall():
            group_ids = [int(gid) for gid in groups.split(',')] if groups else []
            field_groups[(model, name)] = group_ids
            all_group_ids += group_ids

        xml_ids = {}
        if all_group_ids:
            query = """
                SELECT
                    name,
                    module,
                    res_id
                FROM 
                    ir_model_data
                WHERE
                    model = 'res.groups' AND res_id in %s
            """
            cr.execute(query, [tuple(all_group_ids)])
            xml_ids = {group_id: '.'.join([module, name]) for name, module, group_id in cr.fetchall()}

        for (field_model, field_name), group_ids in field_groups.items():
            if field_model in self.env and field_name in self.env[field_model]._fields and (len(group_ids) > 0 or force):
                field_group_xml_ids = [xml_ids.get(gid, str(gid)) for gid in group_ids]
                self.env[field_model]._fields[field_name].groups = ','.join(field_group_xml_ids)

    def _add_manual_fields(self, model):
        super(IrModelFields, self)._add_manual_fields(model)
        cr = self.env.cr
        cr.execute("SELECT id FROM ir_model_fields WHERE model='{}'".format(model._name))
        field_ids = [record['id'] for record in cr.dictfetchall()]
        self.browse(field_ids)._update_field_groups()



class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    @tools.ormcache('xmlid')
    def xmlid_lookup(self, xmlid):
        if isinstance(xmlid, str) and xmlid.isnumeric():
            return False, 'res.groups', int(xmlid)
        return super(IrModelData, self).xmlid_lookup(xmlid)
