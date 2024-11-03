# See LICENSE file for full copyright and licensing details.

import logging
import threading
import time
import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime
from odoo.addons.equip3_manuf_doublebook.models.base_synchro_obj import RPCProxy
from odoo.addons.base.models.ir_model import quote

_logger = logging.getLogger(__name__)


class BaseSynchro(models.TransientModel):
    _inherit = 'base.synchro'

    @api.model
    def query_create(self, model_name, value):
        table = self.env[model_name]._table
        model_fields = self.env[model_name]._fields

        new_value = {}
        m2m_value = {}
        for field_name, field_value in value.items():
            if field_name == 'id':
                continue

            field = model_fields[field_name]
            # one2many handled from inverse, while many2many process after the record created
            if field.type in ('one2many', 'many2many', 'binary') or not field.store:
                if field.type == 'many2many' and field.store and field.comodel_name in ('mrp.plan', 'mrp.plan.line', 'mrp.plan.material', 'mrp.production', 'mrp.workorder', 'mrp.consumption', 'stock.move'):
                    m2m_value[field_name] = field_value
                continue
            elif field.type == 'many2one':
                if isinstance(field_value, tuple) or isinstance(field_value, list):
                    field_value = field_value[0]
                if not self.env[field.comodel_name].browse(field_value or False).exists():
                    continue
            
            field_value = None if field_value is False else field_value
            new_value[field_name] = field_value

        field_names = new_value.keys()
        record = [new_value[field_name] for field_name in field_names]

        query = "INSERT INTO {table} ({cols}) VALUES %s RETURNING id".format(
            table=table,
            cols=', '.join(quote(field_name) for field_name in field_names))
        row = "({this})".format(this=', '.join("%s" for o in field_names))
        query_vals = ', '.join(self.env.cr.mogrify(row, tuple(record)).decode('utf-8') for record in [record])

        self.env.cr.execute(query % query_vals)
        return self.env.cr.fetchone()[0], m2m_value

    @api.model
    def query_m2m_create(self, table, column1, column2, col1_id, col2_ids):
        query = "INSERT INTO {table} ({cols}) VALUES %s".format(
            table=table,
            cols=', '.join(quote(field_name) for field_name in (column1, column2)))
        row = "({this})".format(this=', '.join("%s" for o in range(2)))

        query_vals = ', '.join(self.env.cr.mogrify(row, (col1_id, col2_id)).decode('utf-8') for col2_id in col2_ids)
        self.env.cr.execute(query % query_vals)
        return True

    @api.model
    def _mrp_set_values(self, value, restricted_fields, record_id, model_name, pool, parent_dict):
        for restricted_field in restricted_fields:
            if restricted_field in value:
                del value[restricted_field]
        
        value['base_sync'] = True
        value['base_sync_origin_id'] = record_id

        def parent_from_origin(dest_model_name, origin_parent_id):
            if not origin_parent_id:
                return False
            parent_id = parent_dict.get(dest_model_name, {}).get(str(origin_parent_id), False)
            if parent_id:
                return parent_id
            
            result = pool.get(dest_model_name).get_existed_records(origin_parent_id)
            return result.get(str(origin_parent_id), False)

        def m2o_value(val):
            if isinstance(val, tuple) or isinstance(val, list):
                return val[0]
            return val

        if model_name == 'mrp.estimated.cost':
            value['plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('plan_id')))
            value['production_id'] = parent_from_origin('mrp.production', m2o_value(value.get('production_id')))

        elif model_name == 'stock.move':
            value['state'] = 'draft'
            value['mrp_plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('mrp_plan_id')))
            value['raw_material_production_id'] = parent_from_origin('mrp.production', m2o_value(value.get('raw_material_production_id')))
            value['production_id'] = parent_from_origin('mrp.production', m2o_value(value.get('production_id')))
            value['mrp_workorder_component_id'] = parent_from_origin('mrp.workorder', m2o_value(value.get('mrp_workorder_component_id')))
            value['mrp_workorder_byproduct_id'] = parent_from_origin('mrp.workorder', m2o_value(value.get('mrp_workorder_byproduct_id')))
            value['workorder_id'] = parent_from_origin('mrp.workorder', m2o_value(value.get('workorder_id')))
            value['mrp_consumption_id'] = parent_from_origin('mrp.consumption', m2o_value(value.get('mrp_consumption_id')))
            value['mrp_consumption_byproduct_id'] = parent_from_origin('mrp.consumption', m2o_value(value.get('mrp_consumption_byproduct_id')))
            value['mrp_consumption_finished_id'] = parent_from_origin('mrp.consumption', m2o_value(value.get('mrp_consumption_finished_id')))

        elif model_name == 'mrp.consumption':
            value['name'] = '/'
            value['state'] = 'draft'
            value['workorder_id'] = parent_from_origin('mrp.workorder', m2o_value(value.get('workorder_id')))
            value['manufacturing_order_id'] = parent_from_origin('mrp.production', m2o_value(value.get('manufacturing_order_id')))
            value['manufacturing_plan'] = parent_from_origin('mrp.plan', m2o_value(value.get('manufacturing_plan')))

        elif model_name == 'mrp.workorder':
            value['workorder_id'] = '/'
            value['state'] = 'pending'
            value['production_id'] = parent_from_origin('mrp.production', m2o_value(value.get('production_id')))
            value['mrp_plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('mrp_plan_id')))

        elif model_name == 'mrp.production':
            value['name'] = '/'
            value['state'] = 'draft'
            value['has_clicked_mark_done'] = False
            value['mrp_plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('mrp_plan_id')))

        elif model_name == 'mrp.plan.line':
            value['plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('plan_id')))

        elif model_name == 'mrp.plan.material':
            value['plan_id'] = parent_from_origin('mrp.plan', m2o_value(value.get('plan_id')))

        elif model_name == 'mrp.plan':
            value['plan_id'] = '/'
            value['state'] = 'draft'
        
        return value

    @api.model
    def mrp_synchronize(self, obj, parent_dict, this, that):
        server = obj.server_id

        model_name = obj.model_id.model
        model_desc = obj.model_id.name

        _logger.info('Synchronizing %s...' % (model_desc,))

        module_id = that.get('ir.module.module').search(
            [('name', 'ilike', 'base_synchro'), ('state', '=', 'installed')], limit=1)
        
        if not module_id:
            raise ValidationError(_('If your Synchronization direction is download or both, please install "Multi-DB Synchronization" module in targeted server!'))

        sync_ids = obj.get_record_ids()
        record_ids = [item[0] for item in sync_ids]

        exists = that.get(model_name).get_existed_records(record_ids)
        restricted_fields = list(set([f.name for f in obj.avoid_ids]))

        _logger.info('%s records %s to synchronize...' % (len(sync_ids), model_desc,))
        
        if model_name not in parent_dict:
            parent_dict[model_name] = {}
        
        m2m_relations = {}
        for count, (record_id, last_sync) in enumerate(sync_ids):

            new_id = exists.get(str(record_id))
            if new_id:
                _logger.info('%s record (%s) already synchronized, skipping...' % (model_desc, model_name,))
                if not last_sync:
                    this.get(model_name).browse(record_id).write({'base_sync_last_sync': fields.Datetime.now()})
            else:
                value = this.get(model_name).browse(record_id).read()[0]
                value = this.get('base.synchro')._mrp_set_values(value, restricted_fields, record_id, model_name, that, parent_dict)

                _logger.debug('Creating model %s', model_desc)
                new_id, m2m_value = that.get('base.synchro').query_create(model_name, value)
                m2m_relations[str(new_id)] = m2m_value.copy()
                
                self.env['base.synchro.obj.line'].create({
                    'obj_id': obj.id,
                    'local_id': record_id,
                    'remote_id': new_id,
                })
                self.report_total += 1
                self.report_create += 1

                this.get(model_name).browse(record_id).write({'base_sync_last_sync': fields.Datetime.now()})

                _logger.info('%s/%s records %s synchronized...' % (count + 1, len(sync_ids), model_desc))

            parent_dict[model_name][str(record_id)] = new_id

        obj.write({'m2m_relations': json.dumps(m2m_relations)})
        return parent_dict

    def _set_m2m_relations(self, objects, parent_dict, pool):
        _logger.info('Set many2many relations...')

        for obj in objects:
            model_name = obj.model_id.model
            model_fields = self.env[model_name]._fields
            
            m2m_relations = json.loads(obj.m2m_relations or '{}')

            for that_record_id, m2m_values in m2m_relations.items():
                that_record_id = int(that_record_id)

                for m2m_field_name, this_value_ids in m2m_values.items():
                    if not this_value_ids:
                        continue
                    field = model_fields[m2m_field_name]

                    that_value_ids = []
                    not_found_ids = []
                    for this_value_id in this_value_ids:
                        that_value_id = parent_dict.get(field.comodel_name, {}).get(str(this_value_id), False)
                        if not that_value_id:
                            not_found_ids += [this_value_id]
                        else:
                            that_value_ids += [that_value_id]

                    if not_found_ids:
                        result = pool.get(field.comodel_name).get_existed_records(not_found_ids)
                        that_value_ids += [o for o in result.values() if o]

                    if not that_value_ids:
                        continue

                    pool.get('base.synchro').query_m2m_create(field.relation, field.column1, field.column2, that_record_id, that_value_ids)

    def upload_download(self):
        server = self.server_url
        objects = server.obj_ids
        mrp_objects = objects.filtered(lambda o: o.is_mrp_sync)

        if not mrp_objects:
            return super(BaseSynchro, self).upload_download()
        
        other_objects = objects - mrp_objects
        if mrp_objects and other_objects:
            raise ValidationError(_('cannot synchronize production sync and other sync simultaneously!'))

        self.ensure_one()
        report = []
        list_ids = []
        
        timezone = self._context.get('tz', 'UTC')
        start_date = format_datetime(self.env, fields.Datetime.now(), timezone, dt_format=False)

        pool_this = self.env
        pool_that = RPCProxy(server)

        parent_dict = {}
        for obj in mrp_objects:
            _logger.debug('Start synchro of %s', obj.name)
            parent_dict = self.mrp_synchronize(obj, parent_dict, pool_this, pool_that)

        self._set_m2m_relations(mrp_objects, parent_dict, pool_that)

        for obj in mrp_objects:
            obj.write({
                'm2m_relations': False,
                'synchronize_date': fields.Datetime.now()
            })
        
        end_date = format_datetime(self.env, fields.Datetime.now(), timezone, dt_format=False)
        # Creating res.request for summary results
        if self.user_id:
            request = self.env["res.request"]
            if not report:
                report.append("No exception.")
            summary = """Here is the synchronization report:

     Synchronization started: %s
     Synchronization finished: %s

     Synchronized records: %d
     Records updated: %d
     Records created: %d

     Exceptions:
        """ % (
                start_date,
                end_date,
                self.report_total,
                self.report_write,
                self.report_create,
            )
            summary += "\n".join(report)
            cek = request.create(
                {
                    "name": "Synchronization report",
                    "act_from": self.env.user.id,
                    "date": fields.Datetime.now(),
                    "act_to": self.user_id.id,
                    "body": summary,
                    "res_request_lines" : list_ids,
                }
            )
            return {}
