from odoo import api, fields, models, _
from odoo.osv import expression
from collections import defaultdict
from xmlrpc.client import ServerProxy


class RPCProxyOne(object):
    def __init__(self, server, uid, rpc, resource):
        self.db = server.server_db
        self.uid = uid
        self.password = server.password
        self.rpc = rpc
        self.resource = resource

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.rpc.execute(
            self.db,
            self.uid,
            self.password,
            self.resource,
            name,
            *args
        )


class RPCProxy(object):
    def __init__(self, server):
        self.server = server
        if server.server_url_server:
            local_url = "%s/xmlrpc/common" % (server.server_url_server)
            rpc = ServerProxy(local_url)
            self.uid = rpc.login(server.server_db, server.login, server.password)
            local_url = "%s/xmlrpc/object" % (server.server_url_server)
            self.rpc = ServerProxy(local_url)
        else:
            local_url = "http://%s:%d/xmlrpc/common" % (
                server.server_url,
                server.server_port,
            )
            rpc = ServerProxy(local_url)
            self.uid = rpc.login(server.server_db, server.login, server.password)
            local_url = "http://%s:%d/xmlrpc/object" % (
                server.server_url,
                server.server_port,
            )
            self.rpc = ServerProxy(local_url)

    def get(self, resource):
        return RPCProxyOne(self.server, self.uid, self.rpc, resource)


class BaseSynchroObj(models.Model):
    _inherit = 'base.synchro.obj'

    is_mrp_sync = fields.Boolean(string='Production Sync')
    record_to_sync_ids = fields.One2many('base.synchro.record', 'obj_id', string='Records')

    # technical fields
    is_mrp_field_exist = fields.Boolean(compute='_compute_is_mrp_field_exist')
    is_mrp_need_update = fields.Boolean(compute='_compute_is_mrp_need_update')
    m2m_relations = fields.Text()

    def _is_mrp_field_exist(self):
        self.ensure_one()
        model_name = self.model_id.model
        pool = RPCProxy(self.server_id)
        res = pool.get(model_name).fields_get(allfields=['base_sync_last_sync'])
        return 'base_sync_last_sync' in res

    @api.depends('synchronize_date', 'record_to_sync_ids')
    def _compute_is_mrp_need_update(self):
        for record in self:
            last_sync = record.synchronize_date
            record.is_mrp_need_update = any(o.last_sync < last_sync for o in record.record_to_sync_ids.filtered(lambda o: o.last_sync))

    @api.depends('model_id', 'server_id', 'is_mrp_sync')
    def _compute_is_mrp_field_exist(self):
        for record in self:
            if not record.is_mrp_sync or not record.model_id or not record.server_id:
                record.is_mrp_field_exist = False
                continue
            record.is_mrp_field_exist = record._is_mrp_field_exist()
            
    def get_record_ids(self):
        self.ensure_one()

        model_name = self.model_id.model

        domain = []
        if self._is_mrp_field_exist():
            domain = [('base_sync_last_sync', '=', False)]

        domain = expression.AND([domain, eval(self.domain or '[]')])
        if self.synchronize_date:
            domain = expression.AND([domain, [('create_date', '>=', self.synchronize_date)]])

        return [
            (item.id, item.base_sync_last_sync) 
            for item in self.env[model_name].search(domain)]

    def action_check(self):
        self.ensure_one()

        if not self.is_mrp_sync:
            return

        model_name = self.model_id.model
        that = RPCProxy(self.server_id)
        this = self.env

        sync_ids = self.get_record_ids()
        record_ids = [item[0] for item in sync_ids]
        exists = that.get(model_name).get_existed_records(record_ids)

        record_to_sync_vals = [(5,)]
        for record_id, last_sync in sync_ids:
            this_record = this.get(model_name).browse(record_id)
            that_record = exists.get(str(record_id), False)

            record_to_sync_vals += [(0, 0, {
                'res_model': model_name,
                'res_id': record_id,
                'res_display_name': this_record.display_name,
                'res_create_date': this_record.create_date,
                'synchronized': that_record is not False
            })]

        self.record_to_sync_ids = record_to_sync_vals

class BaseSynchroRecord(models.Model):
    _name = 'base.synchro.record'
    _description = 'Base Synchro Record'

    obj_id = fields.Many2one('base.synchro.obj', string='Base Synchro Object', required=True, ondelete='cascade')
    res_model = fields.Char(string='Record Model', required=True)
    res_id = fields.Integer(string='Record ID', required=True)
    res_display_name = fields.Char(string='Record Name')
    res_create_date = fields.Datetime(string='Record Create Date')
    last_sync = fields.Datetime(string='Last Synchronized', compute='_compute_last_sync')
    synchronized = fields.Boolean()

    def _compute_last_sync(self):
        for record in self:
            last_sync = False
            if record.res_model and record.res_id:
                last_sync = self.env[record.res_model].browse(record.res_id).base_sync_last_sync
            record.last_sync = last_sync

    def action_view_record(self):
        self.ensure_one()
        model = self.env['ir.model'].search([('model', '=', self.res_model)], limit=1)
        return {
            'name': model.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'target': 'current'
        }