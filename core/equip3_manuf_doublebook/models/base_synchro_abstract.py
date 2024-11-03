from odoo import models, fields, api, _


class BaseSync(models.AbstractModel):
    _name = 'base.synchro.abstract'
    _description = 'Abstract Base Synchro'

    base_sync = fields.Boolean()
    base_sync_origin_id = fields.Integer()
    base_sync_last_sync = fields.Datetime(string='Last Synchronized')

    @api.model
    def get_existed_records(self, origin_ids):
        result = {}
        if not origin_ids:
            return result

        if isinstance(origin_ids, int):
            origin_ids = [origin_ids]
        
        self.env.cr.execute("""
        SELECT
            base_sync_origin_id, id
        FROM
            {table}
        WHERE
            base_sync_origin_id IN %s
        ORDER BY
            id
        """.format(table=self._table), [tuple(origin_ids)])
        result = {str(item[0]): item[1] for item in self.env.cr.fetchall()}
        return result
