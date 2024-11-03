# -*- coding: utf-8 -*-


from odoo import api, models, tools
from psycopg2 import ProgrammingError
import hashlib

import logging
_logger = logging.getLogger(__name__)


class ViewCache(models.Model):
    _name = 'ir.ui.view.cache'
    _description = 'Cached views for ir_ui_view'
    _auto = False

    def init(self):
        cr = self._cr
        cr.execute('''select table_name from information_schema.tables
           where table_schema = 'public' and table_name = 'ir_ui_view_cache'
           ''')

        if not cr.fetchone():
            cr.execute('''create table ir_ui_view_cache (
                key character varying not null,
                arch text,
                create_date timestamp without time zone default timezone('utc'::text, now())
            )''')

        cr.execute('select indexname from pg_indexes where indexname = %s', ('ir_ui_view_cache_key_index',))
        if not cr.fetchone():
            cr.execute('create index ir_ui_view_cache_key_index on ir_ui_view_cache using btree (key)')

    @api.model
    def get(self, key):
        self.env.cr.execute('select arch from ir_ui_view_cache where key = %s limit 1', (key, ))
        res = self.env.cr.fetchone()
        return res and res[0]

    @api.model
    def set(self, key, arch):
        try:
            self.env.cr.execute('insert into ir_ui_view_cache (key, arch) values(%s, %s)', (key, arch))
        except Exception as e:
            _logger.exception(e)



class View(models.Model):
    _inherit = 'ir.ui.view'


    # apply ormcache_context decorator unless in dev mode...
    @api.model
    @tools.conditional(
        'xml' not in tools.config['dev_mode'],
        tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'view_id',
                       'tuple(self._context.get(k) for k in self._read_template_keys())'),
    )
    def _read_template(self, view_id):
        if 'xml' in tools.config['dev_mode']:
            return super(View, self)._read_template(view_id)

        cache = self.env['ir.ui.view.cache']
        key = (
            frozenset(self.env.user.groups_id.ids),
            view_id,
            tuple(self._context.get(k) for k in self._read_template_keys()),
        )

        key_hash = hashlib.sha1(str(key).encode('utf-8')).hexdigest()
        r = cache.get(key_hash)

        if r:
            return r

        res = super(View, self)._read_template(view_id)
        cache.set(key_hash, res)

        return res


    @classmethod
    def clear_caches(cls):
        with cls.pool.cursor() as cr:
            try:
                cr.execute('delete from ir_ui_view_cache where true')
            except ProgrammingError as e:
                if 'relation "ir_ui_view_cache" does not exist' in e.pgerror:
                    pass
                else:
                    raise e
        return super(View, cls).clear_caches()
