# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from operator import itemgetter
import json


class BaseSynchroServer(models.Model):
    """Class to store the information regarding server."""

    _name = "base.synchro.server"
    _description = "Synchronized Server"

    name = fields.Char("Server Name", required=True)
    server_url = fields.Char("Server IP")
    server_port = fields.Integer()
    server_url_server = fields.Char("Server URL")
    server_db = fields.Char("Server Database", required=True)
    login = fields.Char("Database UserName", required=True)
    password = fields.Char(required=True)
    obj_ids = fields.One2many(
        "base.synchro.obj", "server_id", "Models", ondelete="cascade"
    )
    select = fields.Selection([("url", "URL"), ("port", "Port")], "Server Type", required=True, default="port")

class BaseSynchroObj(models.Model):
    """Class to store the operations done by wizard."""

    _name = "base.synchro.obj"
    _description = "Register Class"
    _order = "sequence"

    name = fields.Char(required=True)
    domain = fields.Char(required=True, default="[]")
    server_id = fields.Many2one(
        "base.synchro.server", "Server", ondelete="cascade", required=True
    )
    model_id = fields.Many2one("ir.model", "Object to synchronize")
    action = fields.Selection(
        #[("d", "Download"), ("u", "Upload"), ("b", "Both")],
        [("u", "Upload")],
        "Synchronization direction",
        required=True,
        default="u",
    )
    sequence = fields.Integer("Sequence")
    active = fields.Boolean(default=True)
    synchronize_date = fields.Datetime("Latest Synchronization", readonly=False)
    line_id = fields.One2many(
        "base.synchro.obj.line", "obj_id", "IDs Affected", ondelete="cascade"
    )
    avoid_ids = fields.One2many(
        "base.synchro.obj.avoid", "obj_id", "Fields Not Sync."
    )

    field_line = fields.Many2many('ir.model.fields', string="Select Field")
    filter_field_line = fields.Char('ir.model.fields', compute='_compute_filed_copy')

    @api.depends('model_id')
    def _compute_filed_copy(self):
        for record in self:
            field_line_ids = []
            if record.model_id:
                self.env.cr.execute("""
                    SELECT id
                    FROM ir_model_fields
                    WHERE model_id = %s and ttype in ('many2one', 'one2many', 'many2many')
                """ % (record.model_id.id))
                field_line_ids = self.env.cr.fetchall()
            record.filter_field_line = json.dumps([('id','in', list(map(itemgetter(0), field_line_ids)))])


    @api.model
    def get_ids(self, obj, dt, domain=None, action=None):
        if action is None:
            action = {}
        model_obj = self.env[obj]
        if dt:
            w_date = domain + [("write_date", ">=", dt)]
            c_date = domain + [("create_date", ">=", dt)]
            obj_rec = model_obj.search(w_date) | model_obj.search(c_date)
        else:
            obj_rec = model_obj.search(domain)
        result = [
            (
                r.get("write_date") or r.get("create_date"),
                r.get("id"),
                action.get("action", "d"),
            )
            for r in obj_rec.read(["create_date", "write_date"])
        ]
        return result


class BaseSynchroObjAvoid(models.Model):
    """Class to avoid the base synchro object."""

    _name = "base.synchro.obj.avoid"
    _description = "Fields To Not Synchronize"

    name = fields.Char("Field Name", required=True)
    obj_id = fields.Many2one(
        "base.synchro.obj", "Object", required=True, ondelete="cascade"
    )


class BaseSynchroObjLine(models.Model):
    """Class to store object line in base synchro."""

    _name = "base.synchro.obj.line"
    _description = "Synchronized Instances"

    name = fields.Datetime(
        "Date", required=True, default=lambda self: fields.Datetime.now()
    )
    obj_id = fields.Many2one("base.synchro.obj", "Object", ondelete="cascade")
    local_id = fields.Integer("Local ID", readonly=True)
    remote_id = fields.Integer("Remote ID", readonly=True)
