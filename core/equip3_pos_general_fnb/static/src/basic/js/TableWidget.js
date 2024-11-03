odoo.define('equip3_pos_general.TableWidget', function(require) {
    'use strict';

    const TableWidget = require('pos_restaurant.TableWidget');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    const POSTableWidget = (TableWidget) =>
        class extends TableWidget {
            mounted() {
                super.mounted(...arguments);
                var self = this;
                // this.el.addEventListener('mouseenter', function(ev){
                //     self._onHover(ev);
                // });
            }
            _onHover(ev){
                if(!this.__owl__.parent.state.isEditMode){
                    var table = this.props.table;
                    var self = this;
                    $(ev.currentTarget).popover({
                        trigger: 'manual',
                        animation: true,
                        html: true,
                        title: 'Table Info',
                        container: 'body',
                        placement: 'auto',
                        template: '<div class="popover table_info_popover" role="tooltip"><div class="arrow" style="border-color:'+table.color+'"></div><div class="popover-body">sdsd</div></div>'
                    });
                    $(ev.currentTarget).data("bs.popover").config.content = QWeb.render('TableInfoWidget', {table: table, tablePopInfo: this.tablePopInfo, in_time:jQuery('.hm_table_'+table.id+' .table-arrive-in-time').text(), out_time: jQuery('.hm_table_'+table.id+' .table-arrive-out-time').text()});
                    $(ev.currentTarget).popover("show");
                    $(ev.currentTarget).on('mouseleave', function (ev) {
                       $(ev.currentTarget).popover('hide');
                    });
                }
                
            }
            get tablePopInfo() {
                let info = {
                    'checkedIn': null,
                    'amount': 0,
                    'customer_count': 0,
                    'seat_no': '',
                }
                const orders = this.env.pos.get_table_orders(this.props.table);
                if (orders.length > 0) {
                    for (let i=0; i < orders.length; i++) {
                        let order = orders[i]
                        info['checkedIn'] = order['created_time'];
                        info['amount'] = this.env.pos.format_currency(order.get_total_with_tax());
                        info['customer_count'] = order.get_customer_count();
                        info['seat_no'] = '('+order.get_table_order_seat_no(this)+')';
                    }
                    return info
                } else {
                    return info
                }
            }
        };
    Registries.Component.extend(TableWidget, POSTableWidget);

    return TableWidget;
});
