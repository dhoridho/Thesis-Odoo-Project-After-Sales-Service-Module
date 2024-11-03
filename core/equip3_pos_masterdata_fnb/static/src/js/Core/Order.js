odoo.define('equip3_pos_masterdata_fnb.Order', function (require) {
    'use strict';

    const models = require('point_of_sale.models');

    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            _super_Order.initialize.apply(this, arguments);

        },
        init_from_JSON: function (json) {
            let res = _super_Order.init_from_JSON.apply(this, arguments);
            if (json.employee_id) {
                if (this.pos.employee_by_id) {
                    let employee = this.pos.employee_by_id[json.employee_id]
                    if (!employee) {
                        this.employee_id = null
                    }
                } else {
                    this.employee_id = null
                }
            }
            return res;
        },
        export_as_JSON: function () {
            let json = _super_Order.export_as_JSON.apply(this, arguments);
            if (this.employeemeal_employee_id) {
                json.employeemeal_employee_id = this.employeemeal_employee_id
            }
            if (json.employee_id) {
                // todo: default module point_of_sale core odoo define variable employee_id linked to cashier but backend not define employee_id
                // todo: my module have define employee_id, and when force cashier id to employee will have issue
                // todo: so we recheck have employee with cashier id or not, if yes, allow save, else set back null
                if (this.pos.employee_by_id) {
                    let employee = this.pos.employee_by_id[json.employee_id]
                    if (!employee) {
                        json.employee_id = null;
                        this.employee_id = null;
                    }
                } else {
                    json.employee_id = null;
                    this.employee_id = null;
                }

            }
            return json;
        },
        lock_order: async function () {
            const order = this;
            if (order && order.table) {
                let result = await rpc.query({
                    model: 'restaurant.table',
                    method: 'lock_table',
                    args: [[order.table.id], {
                        'locked': true,
                        'customer_name': this.pos.r_customer_name || '',
                        'date_reserve': this.pos.table_reserve_date || false,
                        'clear_interval': this.pos.clear_interval || false
                    }],
                })
                if (result) {
                    const table = this.pos.tables.find(t => t.id == order.table.id)
                    table.locked = true;
                    table.date_reserve = this.pos.table_reserve_date
                    this.pos.set_table(null)
                }
                if (this.pos.pos_bus) {
                    this.pos.pos_bus.send_notification({
                        data: {
                            order: order.export_as_JSON(),
                            table_id: order.table.id,
                            order_uid: order.uid,
                            lock: true,
                            customer_name: this.pos.r_customer_name || '',
                            date_reserve: this.pos.table_reserve_date || false
                        },
                        action: 'lock_table',
                        order_uid: order.uid,
                    })
                }
            }
        },
        get_table_order_seat_no: function(ev) {
            var self = this;
            var seatno = this.get_orderlines().filter((x)=>{return x.required_ask_seat !== ""});
            return seatno.map((x) => x.required_ask_seat).join()
        }
    });

});