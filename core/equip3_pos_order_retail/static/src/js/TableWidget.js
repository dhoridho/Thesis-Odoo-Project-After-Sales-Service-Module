odoo.define('equip3_pos_order_retail.TableWidget', function(require) {
    'use strict';

    const TableWidget = require('pos_restaurant.TableWidget');
    const TableWidgetPOS = require('equip3_pos_general.TableWidget');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    const POSTableWidgetExtend = (TableWidgetPOS) =>
        class extends TableWidgetPOS {
            get tablePopInfo() {
                var res = super.tablePopInfo;
                const orders = this.env.pos.get_table_orders(this.props.table);
                if (orders.length > 0) {
                    for (let i=0; i < orders.length; i++) {
                        let order = orders[i]
                        res['seat_no'] = '('+order.get_table_order_seat_no(this)+')';
                    }
                }
                return res
            }
        };
    Registries.Component.extend(TableWidgetPOS, POSTableWidgetExtend);

    return TableWidgetPOS;
});
