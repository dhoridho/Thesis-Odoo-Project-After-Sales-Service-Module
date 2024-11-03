import base64
import os
from odoo.models import BaseModel,fix_import_export_id_paths,convert_pgerror_not_null,convert_pgerror_unique,convert_pgerror_constraint
from odoo import api,_,tools,models
import odoo
import psycopg2, psycopg2.extensions
from collections import defaultdict, OrderedDict
import logging
from odoo.modules.module import get_module_path
from odoo.tools.lru import LRU
from odoo.tools import CountingStream
import xlsxwriter
import functools
from datetime import datetime


_logger = logging.getLogger(__name__)

PGERROR_TO_OE = defaultdict(
    # shape of mapped converters
    lambda: (lambda model, fvg, info, pgerror: {'message': tools.ustr(pgerror)}), {
    '23502': convert_pgerror_not_null,
    '23505': convert_pgerror_unique,
    '23514': convert_pgerror_constraint,
})


class Base(BaseModel):
    _inherit = 'base'


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if self._context.get('from_import') and operator == '=':
            operator = 'ilike'
        return super(Base, self)._name_search(name, args, operator, limit, name_get_uid=name_get_uid)


    def _load_records(self, data_list, update=False):
        valid_data_list = []
        valid_data_list_index = []
        for i, data in enumerate(data_list):
            if not data['values'].get('_import_skip_create', False):
                valid_data_list += [data]
                valid_data_list_index += [i]
        return super(Base, self)._load_records(valid_data_list, update=update)
    
    @api.model
    def _convert_records_2(self, records, log=lambda a: None):
        """ Converts records from the source iterable (recursive dicts of
        strings) into forms which can be written to the database (via
        self.create or (ir.model.data)._update)

        :returns: a list of triplets of (id, xid, record)
        :rtype: list((int|None, str|None, dict))
        """
        field_names = {name: field.string for name, field in self._fields.items()}
        if self.env.lang:
            field_names.update(self.env['ir.translation'].get_field_string(self._name))

        convert = self.env['ir.fields.converter'].for_model_2(self)

        def _log(base, record, field, exception):
            type = 'warning' if isinstance(exception, Warning) else 'error'
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            exc_vals = dict(base, record=record, field=field_names[field])
            record = dict(base, type=type, record=record, field=field,
                          message=str(exception.args[0]) % exc_vals)
            if len(exception.args) > 1 and exception.args[1]:
                record.update(exception.args[1])
            log(record)

        stream = CountingStream(records)
        for record, extras in stream:
            # xid
            xid = record.get('id', False)
            # dbid
            dbid = False
            if '.id' in record:
                try:
                    dbid = int(record['.id'])
                except ValueError:
                    # in case of overridden id column
                    dbid = record['.id']
                if not self.search([('id', '=', dbid)]):
                    log(dict(extras,
                        type='error',
                        record=stream.index,
                        field='.id',
                        message=_(u"Unknown database identifier '%s'", dbid)))
                    dbid = False

            converted = convert(record, functools.partial(_log, extras, stream.index))

            yield dbid, xid, converted, dict(extras, record=stream.index)
            
    @api.model
    def load_3(self, fields, data,base_import):
        """
        Attempts to load the data matrix, and returns a list of ids (or
        ``False`` if there was an error and no id could be generated) and a
        list of messages.

        The ids are those of the records created and saved (in database), in
        the same order they were extracted from the file. They can be passed
        directly to :meth:`~read`

        :param fields: list of fields to import, at the same index as the corresponding data
        :type fields: list(str)
        :param data: row-major matrix of data to import
        :type data: list(list(str))
        :returns: {ids: list(int)|False, messages: [Message][, lastrow: int]}
        """
        self.flush()

        # determine values of mode, current_module and noupdate
        mode = self._context.get('mode', 'init')
        current_module = self._context.get('module', '__import__')
        noupdate = self._context.get('noupdate', False)
        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self._cr
        cr.execute('SAVEPOINT model_load')

        fields = [fix_import_export_id_paths(f) for f in fields]
        fg = self.fields_get()

        ids = []
        messages = []
        ModelData = self.env['ir.model.data']

        # list of (xid, vals, info) for records to be created in batch
        batch = []
        batch_xml_ids = set()
        # models in which we may have created / modified data, therefore might
        # require flushing in order to name_search: the root model and any
        # o2m
        creatable_models = {self._name}
        for field_path in fields:
            if field_path[0] in (None, 'id', '.id'):
                continue
            model_fields = self._fields
            if isinstance(model_fields[field_path[0]], odoo.fields.Many2one):
                # this only applies for toplevel m2o (?) fields
                if field_path[0] in (self.env.context.get('name_create_enabled_fieds') or {}):
                    creatable_models.add(model_fields[field_path[0]].comodel_name)
            for field_name in field_path:
                if field_name in (None, 'id', '.id'):
                    break

                if isinstance(model_fields[field_name], odoo.fields.One2many):
                    comodel = model_fields[field_name].comodel_name
                    creatable_models.add(comodel)
                    model_fields = self.env[comodel]._fields

        def flush(*, xml_id=None, model=None):
            if not batch:
                return

            assert not (xml_id and model), \
                "flush can specify *either* an external id or a model, not both"

            if xml_id and xml_id not in batch_xml_ids:
                if xml_id not in self.env:
                    return
            if model and model not in creatable_models:
                return

            data_list = [
                dict(xml_id=xid, values=vals, info=info, noupdate=noupdate)
                for xid, vals, info in batch
            ]
            batch.clear()
            batch_xml_ids.clear()

            # try to create in batch
            try:
                with cr.savepoint():
                    recs = self._load_records(data_list, mode == 'update')
                    ids.extend(recs.ids)
                return
            except psycopg2.InternalError as e:
                # broken transaction, exit and hope the source error was already logged
                if not any(message['type'] == 'error' for message in messages):
                    info = data_list[0]['info']
                    messages.append(dict(info, type='error', message=_(u"Unknown database error: '%s'", e)))
                return
            except Exception:
                pass

            errors = 0
            # try again, this time record by record
            for i, rec_data in enumerate(data_list, 1):
                try:
                    with cr.savepoint():
                        rec = self._load_records([rec_data], mode == 'update')
                        ids.append(rec.id)
                except psycopg2.Warning as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='warning', message=str(e)))
                except psycopg2.Error as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='error', **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                    # Failed to write, log to messages, rollback savepoint (to
                    # avoid broken transaction) and keep going
                    errors += 1
                except Exception as e:
                    _logger.debug("Error while loading record", exc_info=True)
                    info = rec_data['info']
                    string_error = str(type(e))
                    string_error = string_error.replace("odoo.exceptions.","")
                    message = (_(u'Unknown error during import:') + u' %s: %s' % (string_error, e))
                    moreinfo = _('Resolve other errors first')
                    messages.append(dict(info, type='error', message=message, moreinfo=moreinfo))
                    # Failed for some reason, perhaps due to invalid data supplied,
                    # rollback savepoint and keep going
                    errors += 1
                if errors >= 10 and (errors >= i / 10):
                    messages.append({
                        'type': 'warning',
                        'message': _(u"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors.")
                    })
                    break

        # make 'flush' available to the methods below, in the case where XMLID
        # resolution fails, for instance
        flush_self = self.with_context(import_flush=flush, import_cache=LRU(1024))

        # TODO: break load's API instead of smuggling via context?
        limit = self._context.get('_import_limit')
        my_context = self.env.context = dict(self.env.context)

        my_context.update({'is_testing':True})
        
        if limit is None:
            limit = float('inf')
        extracted = flush_self._extract_records(fields, data, log=messages.append, limit=limit)

        converted = flush_self._convert_records(extracted, log=messages.append)

        info = {'rows': {'to': -1}}
        for id, xid, record, info in converted:
            if xid:
                xid = xid if '.' in xid else "%s.%s" % (current_module, xid)
                batch_xml_ids.add(xid)
            elif id:
                record['id'] = id
            batch.append((xid, record, info))

        flush()
        if any(message['type'] == 'error' for message in messages):
            base_import.is_valid_record = False
            cr.execute('ROLLBACK TO SAVEPOINT model_load')
            ids = False
            # cancel all changes done to the registry/ormcache
            self.pool.reset_changes()

        nextrow = info['rows']['to'] + 1
        if nextrow < limit:
            nextrow = 0
        base_import.is_tested_record = True
        return {
            'ids': ids,
            'messages': messages,
            'nextrow': nextrow,
        }
    
    @api.model
    def load_2(self, fields, data,log):
        """
        Attempts to load the data matrix, and returns a list of ids (or
        ``False`` if there was an error and no id could be generated) and a
        list of messages.

        The ids are those of the records created and saved (in database), in
        the same order they were extracted from the file. They can be passed
        directly to :meth:`~read`

        :param fields: list of fields to import, at the same index as the corresponding data
        :type fields: list(str)
        :param data: row-major matrix of data to import
        :type data: list(list(str))
        :returns: {ids: list(int)|False, messages: [Message][, lastrow: int]}
        """
        self.flush()

        # determine values of mode, current_module and noupdate
        mode = self._context.get('mode', 'init')
        current_module = self._context.get('module', '__import__')
        noupdate = self._context.get('noupdate', False)
        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self._cr
        cr.execute('SAVEPOINT model_load')

        fields = [fix_import_export_id_paths(f) for f in fields]
        fg = self.fields_get()

        ids = []
        messages = []
        ModelData = self.env['ir.model.data']

        # list of (xid, vals, info) for records to be created in batch
        batch = []
        batch_xml_ids = set()
        # models in which we may have created / modified data, therefore might
        # require flushing in order to name_search: the root model and any
        # o2m
        creatable_models = {self._name}
        for field_path in fields:
            if field_path[0] in (None, 'id', '.id'):
                continue
            model_fields = self._fields
            if isinstance(model_fields[field_path[0]], odoo.fields.Many2one):
                # this only applies for toplevel m2o (?) fields
                if field_path[0] in (self.env.context.get('name_create_enabled_fieds') or {}):
                    creatable_models.add(model_fields[field_path[0]].comodel_name)
            for field_name in field_path:
                if field_name in (None, 'id', '.id'):
                    break

                if isinstance(model_fields[field_name], odoo.fields.One2many):
                    comodel = model_fields[field_name].comodel_name
                    creatable_models.add(comodel)
                    model_fields = self.env[comodel]._fields

        def flush(*, xml_id=None, model=None):
            if not batch:
                return

            assert not (xml_id and model), \
                "flush can specify *either* an external id or a model, not both"

            # if xml_id and xml_id not in batch_xml_ids:
            #     if xml_id not in self.env:
            #         return
            
            # if model and model not in creatable_models:
            #     return

            data_list = [
                dict(xml_id=xid, values=vals, info=info, noupdate=noupdate)
                for xid, vals, info in batch
            ]
            batch.clear()
            batch_xml_ids.clear()

            # try to create in batch
            try:
                with cr.savepoint():
                    recs = self._load_records(data_list, mode == 'update')
                    ids.extend(recs.ids)
                return
            except psycopg2.InternalError as e:
                # broken transaction, exit and hope the source error was already logged
                if not any(message['type'] == 'error' for message in messages):
                    info = data_list[0]['info']
                    messages.append(dict(info, type='error', message=_(u"Unknown database error: '%s'", e)))
                return
            except Exception:
                pass

            errors = 0
            # try again, this time record by record
            for i, rec_data in enumerate(data_list, 1):
                try:
                    with cr.savepoint():
                        rec = self._load_records([rec_data], mode == 'update')
                        ids.append(rec.id)
                except psycopg2.Warning as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='warning', message=str(e)))
                except psycopg2.Error as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='error', **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                    # Failed to write, log to messages, rollback savepoint (to
                    # avoid broken transaction) and keep going
                    errors += 1
                except Exception as e:
                    _logger.debug("Error while loading record", exc_info=True)
                    info = rec_data['info']
                    message = (_(u'Unknown error during import:') + u' %s: %s' % (type(e), e))
                    moreinfo = _('Resolve other errors first')
                    messages.append(dict(info, type='error', message=message, moreinfo=moreinfo))
                    # Failed for some reason, perhaps due to invalid data supplied,
                    # rollback savepoint and keep going
                    errors += 1
                if errors >= 10 and (errors >= i / 10):
                    messages.append({
                        'type': 'warning',
                        'message': _(u"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors.")
                    })
                    break

        # make 'flush' available to the methods below, in the case where XMLID
        # resolution fails, for instance
        flush_self = self.with_context(import_flush=flush, import_cache=LRU(1024))

        # TODO: break load's API instead of smuggling via context?
        limit = self._context.get('_import_limit')
        my_context = self.env.context = dict(self.env.context)
        my_context.update({'is_import':True})
        if limit is None:
            limit = float('inf')
        extracted = flush_self._extract_records(fields, data, log=messages.append, limit=limit)
        converted = flush_self._convert_records_2(extracted, log=messages.append)
        info = {'rows': {'to': -1}}
        messages_error = []
        log.excel_fields = fields

        for id, xid, record, info in converted:
            number_row = info['record'] + 1
            total_line_progress = number_row
            if info.get('rows'):
                if 'from' in info['rows'] and 'to' in info['rows']:
                    diff_rows = info['rows']['to'] - info['rows']['from']
                    if diff_rows:
                        diff_rows+=1
                    if not log.count_child_line:
                        log.count_child_line = str(number_row)+':'+str(diff_rows)
                    else:
                        old_child_line = int(log.count_child_line.split(':')[1])
                        if int(log.count_child_line.split(':')[0]) < number_row:
                            log.count_child_line = str(number_row)+':'+str(diff_rows+old_child_line)
                        total_line_progress+=old_child_line


                    total_line_progress += diff_rows or 1

            data_append = eval(log.list_data)
            log.total_progress = log.total_progress + 1

            self.env.cr.commit()
            if xid:
                xid = xid if '.' in xid else "%s.%s" % (current_module, xid)
                batch_xml_ids.add(xid)
            elif id:
                record['id'] = id
            data_append.extend(ids)
            log.list_data = str(data_append)
            log._compute_inserted_record() 
            # log.inserted_record = len(set(item for item in eval(log.list_data) if item is not False))
            full_messages = messages
            batch.append((xid, record, info))
            flush()
            full_messages = full_messages + messages
            filtered_error = [d for d in full_messages if d['type'] == 'error']
            unique_error_keys = {(d['rows']['from'], d['rows']['to'], d['type'], d['message']): d for d in filtered_error}.values()
            final_data_error = list(unique_error_keys)
            if final_data_error:
                check_list =  [d for d in final_data_error if d not in eval(log.list_message_error)]
                if check_list:
                    final_data_append = eval(log.list_message_error) 
                    final_data_append.extend(check_list)
                    log.list_message_error = str(final_data_append)
            self.env.cr.commit()

            log.total_line_progress = total_line_progress + log.count_empty_row + log.total_latest_count_total_line
            log.latest_count_total_line = total_line_progress
  
    
            
        to_delete = eval(log.to_delete)
        required_record = []
        data_append = eval(log.list_data)
        data_append.extend(ids)
        log.list_data = str(data_append)
        
        # log.inserted_record = len(set(item for item in eval(log.list_data) if item is not False))
        self.env.cr.commit()
        if eval(log.list_message_error):
            for me in eval(log.list_message_error):
                if me['type'] == 'error':
                    new_log_excel = eval(log.excel_data)
                    new_log_excel[me['rows']['from']].append(me['message'])
                    log.excel_data = new_log_excel
                    to_delete.append(me['rows']['from'])
                    log.to_delete = to_delete
                    if 'required' in me['message']:
                        not_insert = "Not inserted Record"
                        required_record.append(me['rows']['from'])
                        log.skipped_record = log.skipped_record + 1
                        log.error_log = log.error_log + f"\n\n############\n{not_insert if 'required' in me['message'] else ''}  {me['field'] if 'field' in me else '-'} {me['message']}  {new_log_excel[me['rows']['from']]}" if  log.error_log else f"{not_insert if 'required' in me['message'] else ''}  {me['field'] if 'field' in me else '-'} {me['message']}  {new_log_excel[me['rows']['from']]}"
                        self.env.cr.commit()
                    else:
                        log.error_log = log.error_log + f"\n\n############\n{me['field'] if 'field' in me else '-'}  {me['message']}  {new_log_excel[me['rows']['from']]}" if  log.error_log else f"{not_insert if 'required' in me['message'] else ''}  {me['field'] if 'field' in me else '-'} {me['message']}  {new_log_excel[me['rows']['from']]}"
                        self.env.cr.commit()
                log.error_record = len(set(to_delete))
        self.env.cr.commit()
        
        ICPSudo = self.env['ir.config_parameter'].sudo()
        is_split_processing = ICPSudo.get_param('equip3_base_import_extend.is_split_processing')
        if not is_split_processing:
            if eval(log.to_delete):
                to_write = [eval(log.excel_data)[i] for i in set(eval(log.to_delete))]
                excel_filename = f'error_data_import' + '.xlsx'
                module_path = get_module_path('equip3_base_import_extend')
                fpath = module_path + '/generated_files'
                if not os.path.isdir(fpath):
                    os.mkdir(fpath)
                workbook = xlsxwriter.Workbook(module_path + '/generated_files/' + excel_filename)
                worksheet = workbook.add_worksheet()
                worksheet.set_column(0, 20, 17)
                col = -1    
                for header in range(len(fields)):
                    col+=1
                    worksheet.write(0,col,fields[header][0])
                
                row_err = 0
                row_data_len = -1
                for rec_error in to_write:
                    row_err+=1
                    row_data_len+=1
                    col_err = -1
                    for rec_error_data in range(len(rec_error)):
                        col_err+=1
                        worksheet.write(row_err,col_err,rec_error[rec_error_data])
                        
                        
                workbook.close()
                with open(module_path + '/generated_files/' + excel_filename, 'rb') as opened_file:
                    base64_csv_file = base64.b64encode(opened_file.read())
                    log.file_error_records = base64_csv_file
                    log.file_error_name = excel_filename
                self.env.cr.commit()


        log.fix_total_insert_record = log.total_record - log.error_record
        if log.fix_total_insert_record != log.total_record:
            log.state = 'partially_done'
            log.completed_date = datetime.now()
        else:
            log.state = 'done'
            log.completed_date = datetime.now()
        log.total_line_progress = log.total_line

        # log_history = self.env['import.log.history'].sudo().create({'name':log.name,
        #                                                      'import_datetime':log.import_datetime,
        #                                                      'model_id':log.model_id,
        #                                                      'cron_running':log.cron_running,
        #                                                      'inserted_record':log.inserted_record,
        #                                                      'skipped_record':log.skipped_record,
        #                                                      'error_record':log.error_record,
        #                                                      'file_error_records':log.file_error_records,
        #                                                      'file_error_name':log.file_error_name,
        #                                                      'total_record':log.total_record,
        #                                                      'total_progress_char':log.total_progress_char,
        #                                                      'error_log':log.error_log,
        #                                                      'state':log.state,
        #                                                      'completed_date':log.completed_date,
        #                                                      'total_line':log.total_line,
        #                                                      'total_line_progress':log.total_line_progress,
        #                                                      'total_line_char':log.total_line_char,
        #                                                      'batch_count':log.batch_count,
        #                                                      'list_data':log.list_data,
        #                                                      })
        # log.log_history_id = log_history.id
        self.env.cr.commit()
        log._compute_inserted_record() 
        nextrow = info['rows']['to'] + 1
        if nextrow < limit:
            nextrow = 0
        return {
            'ids': ids,
            'messages': messages,
            'nextrow': nextrow,
        }