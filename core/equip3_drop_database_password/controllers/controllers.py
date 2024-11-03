# -*- coding: utf-8 -*-
#############################################################################
from contextlib import closing
import shutil
import threading
from lxml import html
import odoo
import os
from odoo import http
from odoo.service.db import _drop_conn, check_db_management_enabled, list_dbs
from odoo.service.server import memory_info
from odoo.tools.misc import file_open
from odoo.addons.web.controllers.main import Database
from odoo.http import NO_POSTMORTEM, content_disposition, dispatch_rpc, replace_request_password,request
from passlib.context import CryptContext
from odoo.tools.config import configmanager
import jinja2
import logging
import time
from psycopg2 import sql
try:
    import psutil
except ImportError:
    psutil = None
import sys
if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.web', "views")
    import sys
import jinja2
env = jinja2.Environment(loader=loader, autoescape=True)
crypt_context = CryptContext(schemes=['pbkdf2_sha512', 'plaintext'],
                             deprecated=['plaintext'])

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'
db_monodb = http.db_monodb
_logger = logging.getLogger(__name__)
rpc_request = logging.getLogger(__name__ + '.rpc.request')
rpc_response = logging.getLogger(__name__ + '.rpc.response')


class customConfigManager(configmanager):    
    
    def verify_admin_password_drop(self, password):
        stored_hash = odoo.tools.config.get('delete_password',False)
        if not stored_hash:
            # empty password/hash => authentication forbidden
            return False
        result, updated_hash = crypt_context.verify_and_update(password, stored_hash)
        if result:
            if updated_hash:
                self.options['delete_password'] = updated_hash
            return True
            



class Database(Database):
    def check_super(self,passwd):
        if passwd and customConfigManager().verify_admin_password_drop(passwd):
            return True
        raise odoo.exceptions.AccessDenied()
        
    def dispatch(self,method, params):
        g = globals()
        exp_method_name = 'exp_' + method
        if method in ['db_exist', 'list', 'list_lang', 'server_version']:
            return g[exp_method_name](*params)
        elif exp_method_name in g:
            passwd = params[0]
            params = params[1:]
            self.check_super(passwd)
            return g[exp_method_name](*params)
        else:
            raise KeyError("Method not found: %s" % method)
        
        
    def dispatch_rpc(self,service_name, method, params):
        try:
            rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
            rpc_response_flag = rpc_response.isEnabledFor(logging.DEBUG)
            if rpc_request_flag or rpc_response_flag:
                start_time = time.time()
                start_memory = 0
                if psutil:
                    start_memory = memory_info(psutil.Process(os.getpid()))
                if rpc_request and rpc_response_flag:
                    odoo.netsvc.log(rpc_request, logging.DEBUG, '%s.%s' % (service_name, method), replace_request_password(params))

            threading.current_thread().uid = None
            threading.current_thread().dbname = None
            if service_name == 'common':
                dispatch = odoo.service.common.dispatch
            elif service_name == 'db':
                dispatch = self.dispatch
            elif service_name == 'object':
                dispatch = odoo.service.model.dispatch
            result = dispatch(method, params)

            if rpc_request_flag or rpc_response_flag:
                end_time = time.time()
                end_memory = 0
                if psutil:
                    end_memory = memory_info(psutil.Process(os.getpid()))
                logline = '%s.%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % (service_name, method, end_time - start_time, start_memory / 1024, end_memory / 1024, (end_memory - start_memory)/1024)
                if rpc_response_flag:
                    odoo.netsvc.log(rpc_response, logging.DEBUG, logline, result)
                else:
                    odoo.netsvc.log(rpc_request, logging.DEBUG, logline, replace_request_password(params), depth=1)

            return result
        except NO_POSTMORTEM:
            raise
        except Exception as e:
            _logger.exception(odoo.tools.exception_to_unicode(e))
            odoo.tools.debugger.post_mortem(odoo.tools.config, sys.exc_info())
            raise

    
    def _render_template_drop(self, **d):
        d.setdefault('manage',True)
        d['insecure'] = customConfigManager().verify_admin_password_drop('admin')
        d['list_db'] = odoo.tools.config['list_db']
        d['langs'] = odoo.service.db.exp_list_lang()
        d['countries'] = odoo.service.db.exp_list_countries()
        d['pattern'] = DBNAME_PATTERN
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
            d['incompatible_databases'] = odoo.service.db.list_db_incompatible(d['databases'])
        except odoo.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]
        return env.get_template("database_manager.html").render(d)
 
    

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, master_pwd, name):
        try:
            self.dispatch_rpc('db','drop', [master_pwd, name])
            request._cr = None  # dropping a database leads to an unusable cursor
            return http.local_redirect('/web/database/manager')
        except Exception as e:
            error = "Database deletion error: %s" % (str(e) or repr(e))
            return self._render_template_drop(error=error)
        
@check_db_management_enabled
def exp_drop(db_name):
    if db_name not in list_dbs(True):
        return False
    odoo.modules.registry.Registry.delete(db_name)
    odoo.sql_db.close_db(db_name)

    db = odoo.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        cr.autocommit(True) # avoid transaction block
        _drop_conn(cr, db_name)

        try:
            cr.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(db_name)))
        except Exception as e:
            _logger.info('DROP DB: %s failed:\n%s', db_name, e)
            raise Exception("Couldn't drop database %s: %s" % (db_name, e))
        else:
            _logger.info('DROP DB: %s', db_name)

    fs = odoo.tools.config.filestore(db_name)
    if os.path.exists(fs):
        shutil.rmtree(fs)
    return True
