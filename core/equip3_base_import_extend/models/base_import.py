from odoo import fields,models,api,_
import logging
import psycopg2
from datetime import datetime
import operator
import itertools
from ast import literal_eval
import numpy as np
import json
from pytz import timezone, UTC, utc
import pytz
from odoo.exceptions import ValidationError,UserError

_logger = logging.getLogger(__name__)



class Import(models.TransientModel):
    _inherit = 'base_import.import'
    
    is_valid_record = fields.Boolean(default=False)
    is_tested_record = fields.Boolean(default=False)
    is_imported = fields.Boolean(default=False)
    range_data = fields.Integer()
    total_line = fields.Integer()
    data_import = fields.Text()


    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        if self._context.get('import_from_log'):
            try:
                super(Import, self)._parse_float_from_data(data, index, name, options)
            except:
                for line in data:
                    line[index] = line[index]
        else:
            super(Import, self)._parse_float_from_data(data, index, name, options)


    @api.model
    def _parse_date_from_data(self, data, index, name, field_type, options):
        if self._context.get('import_from_log'):
            try:
                super(Import, self)._parse_date_from_data(data, index, name, field_type, options)
            except:
                for line in data:
                    line[index] = line[index]
        else:
            super(Import, self)._parse_date_from_data(data, index, name, field_type, options)
        


    def _read_file(self, options):
        if self._context.get('import_from_log'):
            res_data_import = self._context['import_from_log'].data_import
            res = json.loads(res_data_import)
        else:
            res = super(Import, self)._read_file(options)
        count = 0
        list_data = list(res)
        data_import = list_data
        for data in list_data:
            validation_text = str(data).replace(' ','').replace('`','').replace("'","").replace(',','').replace('[','').replace(']','')
            if len(validation_text) <= 5:
                del list_data[count]
            count+=1

        list_data = iter(list_data)
        if not self._context.get('import_from_log'):
            self.data_import = data_import
        return list_data


    def _parse_import_data_log(self, data, import_fields, options,log):
        """ Lauch first call to _parse_import_data_recursive with an
        empty prefix. _parse_import_data_recursive will be run
        recursively for each relational field.
        """
        return self._parse_import_data_recursive(log.model_id, '', data, import_fields, options)


    @api.model
    def _convert_import_data(self, fields, options):
        """ Extracts the input BaseModel and fields list (with
            ``False``-y placeholders for fields to *not* import) into a
            format Model.import_data can use: a fields list without holes
            and the precisely matching data matrix

            :param list(str|bool): fields
            :returns: (data, fields)
            :rtype: (list(list(str)), list(str))
            :raises ValueError: in case the import data could not be converted
        """
        # Get indices for non-empty fields
        indices = [index for index, field in enumerate(fields) if field]
        if not indices:
            raise ValueError(_("You must configure at least one field to import"))
        # If only one index, itemgetter will return an atom rather
        # than a 1-tuple
        if len(indices) == 1:
            mapper = lambda row: [row[indices[0]]]
        else:
            mapper = operator.itemgetter(*indices)
        # Get only list of actually imported fields
        import_fields = [f for f in fields if f]

        rows_to_import = self._read_file(options)
        if options.get('headers'):
            rows_to_import = itertools.islice(rows_to_import, 1, None)

        data = []
        empty_row = 0
        dryrun = self._context.get('dryrun')
        import_limit = int(self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.test_import_batch_limit'))
        limit_split_line_import = int(self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.limit_split_line_import'))
        count_row = 0

        for row in map(mapper, rows_to_import):
            if any(row):
                count_row+=1
                if count_row > import_limit and dryrun and self.res_model != 'account.move':
                    break
                data.append(list(row))
            else:
                empty_row+=1
        if options.get('import_log'):
            options['import_log'].count_empty_row = empty_row

        # slicing needs to happen after filtering out empty rows as the
        # data offsets from load are post-filtering
        return data[options.get('skip'):], import_fields
        
    
    
    
    def do_scheduler(self, fields, columns, options, log,dryrun=False):
        if self:
            self.ensure_one()
        self._cr.execute('SAVEPOINT import')
        log.cron_running = datetime.now()
        options['import_log'] = log
        self.env.cr.commit()


        try:
            data, import_fields = self._convert_import_data(fields, options)
            # Parse date and float field
            data = self._parse_import_data_log(data, import_fields, options,log)
        except ValueError as error:
            if self._context.get('import_from_log'):
                raise UserError(_(str(error)+'\n'+'Log name:'+log.name))
            return {
                'messages': [{
                    'type': 'error',
                    'message': str(error) ,
                    'record': False,
                }]
            }

        if not log.excel_data:
            log.excel_data = data
        if log.state == 'on_queue':
            log.total_record = sum(1 for sublist in data if sublist[0] != '')
            
        if log.state == 'on_queue':
            log.state = 'running'
        self.env.cr.commit()
        _logger.info('importing %d rows...', len(data))
        name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
        import_limit = len(data)
        # self.env[log.model_id].recompute = False
        model = self.sudo().env[log.model_id].with_context(prefetch_fields=False,tracking_disable=True,import_file=True, name_create_enabled_fields=name_create_enabled_fields, _import_limit=import_limit,from_import=1)
        import_result = model.load_2(import_fields, data,log)
        _logger.info('done')

        # If transaction aborted, RELEASE SAVEPOINT is going to raise
        # an InternalError (ROLLBACK should work, maybe). Ignore that.
        # TODO: to handle multiple errors, create savepoint around
        #       write and release it in case of write error (after
        #       adding error to errors array) => can keep on trying to
        #       import stuff, and rollback at the end if there is any
        #       error in the results.
        # try:
        #     if dryrun:
        #         self._cr.execute('ROLLBACK TO SAVEPOINT import')
        #         # cancel all changes done to the registry/ormcache
        #         self.pool.clear_caches()
        #         self.pool.reset_changes()
        #     else:
        #         self._cr.execute('RELEASE SAVEPOINT import')
        # except psycopg2.InternalError:
        #     pass

        # Insert/Update mapping columns when import complete successfully
        if import_result['ids'] and options.get('headers'):
            BaseImportMapping = self.env['base_import.mapping']
            for index, column_name in enumerate(columns):
                if column_name:
                    # Update to latest selected field
                    mapping_domain = [('res_model', '=', self.res_model), ('column_name', '=', column_name)]
                    column_mapping = BaseImportMapping.search(mapping_domain, limit=1)
                    if column_mapping:
                        if column_mapping.field_name != fields[index]:
                            column_mapping.field_name = fields[index]
                    else:
                        BaseImportMapping.create({
                            'res_model': self.res_model,
                            'column_name': column_name,
                            'field_name': fields[index]
                        })
        
        if 'name' in import_fields:
            index_of_name = import_fields.index('name')
            skipped = options.get('skip', 0)
            # pad front as data doesn't contain anythig for skipped lines
            r = import_result['name'] = [''] * skipped
            # only add names for the window being imported
            r.extend(x[index_of_name] for x in data[:import_limit])
            # pad back (though that's probably not useful)
            r.extend([''] * (len(data) - (import_limit or 0)))
        else:
            import_result['name'] = []

        skip = len(data)
        # convert load's internal nextrow to the imported file's
        if import_result['nextrow']: # don't update if nextrow = 0 (= no nextrow)
            import_result['nextrow'] += skip

        
        

        return import_result
    
    
    def do(self, fields, columns, options, dryrun=False):
      
        """ Actual execution of the import

        :param fields: import mapping: maps each column to a field,
                       ``False`` for the columns to ignore
        :type fields: list(str|bool)
        :param columns: columns label
        :type columns: list(str|bool)
        :param dict options:
        :param bool dryrun: performs all import operations (and
                            validations) but rollbacks writes, allows
                            getting as much errors as possible without
                            the risk of clobbering the database.
        :returns: A list of errors. If the list is empty the import
                  executed fully and correctly. If the list is
                  non-empty it contains dicts with 3 keys ``type`` the
                  type of error (``error|warning``); ``message`` the
                  error message associated with the error (a string)
                  and ``record`` the data which failed to import (or
                  ``false`` if that data isn't available or provided)
        :rtype: dict(ids: list(int), messages: list({type, message, record}))
        """
        options.update({"action_context":self._context})  
        if int(self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.test_import_batch_limit')) == 0:
            return {
                'messages': [{
                    'type': 'error',
                    'message': "Please Set Test Import Rows Limit on settings or triiger save on settings",
                    'record': False,
                }]
            }
        if fields and fields[0]!='id':
            return {
                'messages': [{
                    'type': 'error',
                    'message': "Please Set External Id in first column",
                    'record': False,
                }]
            }
        
        if not dryrun:
          
            if not self.is_tested_record:
                return {
                'messages': [{
                    'type': 'error',
                    'message': "Please Test The Record First",
                    'record': False,
                }]
            }
            if not self.is_valid_record:
                return {
                'messages': [{
                    'type': 'error',
                    'message': "Record is not valid",
                    'record': False,
                }]
            }
            if self.is_imported:
                return {
                'messages': [{
                    'type': 'error',
                    'message': "Record is already imported",
                    'record': False,
                }]
            }

            limit_split_line_import = int(self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.limit_split_line_import'))
            if self.total_line <= limit_split_line_import:
                import_datetime = datetime.now()
                import_datetime_tz = datetime.now(timezone(self.env.user.tz))
                import_log = self.env['import.log'].sudo().create({'name':self.file_name+' ['+datetime.strftime(import_datetime_tz, "%Y-%m-%d %H:%M:%S")+']',
                                                                   'model_id':self.res_model,
                                                                   'file':self.file,
                                                                   'file_name':self.file_name,
                                                                   'file_type':self.file_type,
                                                                   'options':options,
                                                                   'field':fields,
                                                                   'column':columns,
                                                                   'total_record':self.total_line,
                                                                   'total_line': self.total_line,
                                                                   'import_datetime':import_datetime,
                                                                   })

                if import_log:
                    full_data_import = literal_eval(self.data_import)
                    self.data_import = json.dumps(full_data_import, separators=(',', ':'))
                    import_log.data_import = self.data_import
                    self.data_import = False
                    self.is_imported = True
            else:
                have_child = False
                count_col = 0
                column_parent = []
                column_child_one2many = []
                for field_header in fields:
                    if field_header:
                        field_header = field_header.split('/')
                        if len(field_header) > 1:
                            check_field = self.env['ir.model.fields'].search([('name','=',field_header[0]),('model_id.model','=',self.res_model),('ttype','=','one2many')],limit=1)
                            if check_field:
                                column_child_one2many.append(count_col)
                                have_child = True
                            else:
                                column_parent.append(count_col)
                        else:
                            column_parent.append(count_col)
                    count_col += 1


                total_line = self.total_line
                count_batch = 0
                import_datetime = datetime.now()
                import_datetime_tz = datetime.now(timezone(self.env.user.tz))
                full_data_import = literal_eval(self.data_import)
                header_line = False
                new_data_import = []
                last_parent = False
                if options.get('headers'):
                    header_line = full_data_import[0]
                    new_data_import.append(header_line)
                parent_id = False
                while total_line:
                    row_parent = 0
                    count_batch += 1
                    line_row = limit_split_line_import
                    if total_line < limit_split_line_import:
                        line_row = total_line
                    if total_line < limit_split_line_import:
                        total_line = 0

                    if count_batch == 1:
                        first_row = 0
                        if options.get('headers'):
                            first_row = 1
                        first_row_in_line = first_row
                        end_row = line_row +1
                        data_import = new_data_import + np.array(full_data_import[first_row:end_row]).tolist()
                        base_import_id = self.id
                        base_import_rec = self
                        base_import_rec.file = False
                        base_import_rec.data_import = json.dumps(data_import, separators=(',', ':'))
                    else:
                        first_row = end_row 
                        end_row += line_row 
                        data_import = new_data_import
                        first_row_data = np.array(full_data_import[first_row:first_row+1]).tolist()
                        if have_child:
                            first_record_not_parent = False
                            for cp in column_parent:
                                if np.array(full_data_import[first_row:end_row]).tolist()[0][cp]:
                                    first_record_not_parent = True
                                    break
                            if not first_record_not_parent:
                                check_loop = False
                                for x_line in reversed(np.array(full_data_import[first_row_in_line:first_row]).tolist()):
                                    for cp in column_parent:
                                        if x_line[cp]:
                                            last_parent = [x_line]
                                            check_loop = True
                                            break
                                    if check_loop:
                                        break
                                if last_parent:
                                    for cp in column_child_one2many:
                                        last_parent[0][cp] = first_row_data[0][cp]
                                    first_row+=1
                                    row_parent = 1
                                    data_import = data_import + last_parent

                        data_import = data_import + np.array(full_data_import[first_row:end_row]).tolist()
                        base_import_rec = self.copy({
                            'data_import':json.dumps(data_import, separators=(',', ':'))
                        })
                        base_import_id = base_import_rec.id

                
                    import_log = self.env['import.log'].sudo().create({'name':self.file_name +' ['+datetime.strftime(import_datetime_tz, "%Y-%m-%d %H:%M:%S")+']',
                       'batch_count':count_batch,
                       'model_id':self.res_model,
                       'file':self.file,
                       'file_name':self.file_name ,
                       'file_type':self.file_type,
                       'options':options,
                       'field':fields,
                       'column':columns,
                       'total_record':line_row,
                       'total_line': line_row,
                       'import_datetime':import_datetime
                       })
                    if import_log:
                        base_import_rec.is_imported = True
                        import_log.data_import = base_import_rec.data_import
                        base_import_rec.data_import = False
                    if total_line >= limit_split_line_import:
                        total_line-= limit_split_line_import
   


            return {
                'messages': [{
                    'type': 'schedule_import',
                    'message': "Scheduled Import is running in the background, you can close the page now.",
                    'record': False,
                }]
            }

        self.ensure_one()
        self._cr.execute('SAVEPOINT import')
        
      

        try:
            data, import_fields = self.with_context(dryrun=dryrun)._convert_import_data(fields, options)
            # Parse date and float field
  
            data = self._parse_import_data(data, import_fields, options)
     
        except ValueError as error:
            return {
                'messages': [{
                    'type': 'error',
                    'message': str(error),
                    'record': False,
                }]
            }

        _logger.info('importing %d rows...', len(data))
        
        name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
        import_limit = int(self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.test_import_batch_limit'))
        model = self.env[self.res_model].with_context(import_file=True, name_create_enabled_fields=name_create_enabled_fields, _import_limit=import_limit,from_import=1)
        import_result = model.load_3(import_fields, data,self)
        _logger.info('done')

        # If transaction aborted, RELEASE SAVEPOINT is going to raise
        # an InternalError (ROLLBACK should work, maybe). Ignore that.
        # TODO: to handle multiple errors, create savepoint around
        #       write and release it in case of write error (after
        #       adding error to errors array) => can keep on trying to
        #       import stuff, and rollback at the end if there is any
        #       error in the results.
        try:
            if dryrun:
                self._cr.execute('ROLLBACK TO SAVEPOINT import')
                # cancel all changes done to the registry/ormcache
                self.pool.clear_caches()
                self.pool.reset_changes()
            else:
                self._cr.execute('RELEASE SAVEPOINT import')
        except psycopg2.InternalError:
            pass

        # Insert/Update mapping columns when import complete successfully
        if import_result['ids'] and options.get('headers'):

            # DONT MERGE/MOVE THIS CODE
            data_import = self._read_file(options)
           
            total_line = len(list(data_import))
            if options.get('headers'):
                total_line-=1
            if total_line > 0:
                self.write({'total_line':total_line})
             # //////////////////////////////////


            if self.range_data == 0:
                self.write({'range_data':sum(1 for sublist in data if sublist[0] != '')})
            self.write({'is_valid_record':True})
            BaseImportMapping = self.env['base_import.mapping']
            for index, column_name in enumerate(columns):
                if column_name:
                    # Update to latest selected field
                    mapping_domain = [('res_model', '=', self.res_model), ('column_name', '=', column_name)]
                    column_mapping = BaseImportMapping.search(mapping_domain, limit=1)
                    if column_mapping:
                        if column_mapping.field_name != fields[index]:
                            column_mapping.field_name = fields[index]
                    else:
                        BaseImportMapping.create({
                            'res_model': self.res_model,
                            'column_name': column_name,
                            'field_name': fields[index]
                        })
        if 'name' in import_fields:
            index_of_name = import_fields.index('name')
            skipped = options.get('skip', 0)
            # pad front as data doesn't contain anythig for skipped lines
            r = import_result['name'] = [''] * skipped
            # only add names for the window being imported
            r.extend(x[index_of_name] for x in data[:import_limit])
            # pad back (though that's probably not useful)
            r.extend([''] * (len(data) - (import_limit or 0)))
        else:
            import_result['name'] = []

        skip = len(data)
        # convert load's internal nextrow to the imported file's
        if import_result['nextrow']: # don't update if nextrow = 0 (= no nextrow)
            import_result['nextrow'] += skip

        return import_result