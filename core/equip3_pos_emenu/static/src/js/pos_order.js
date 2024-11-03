odoo.define('equip3_pos_emenu.pos_order', function (require) {
    'use strict';
    
    const core = require('web.core');
    const QWeb = core.qweb;
    const Registries = require('point_of_sale.Registries');
    const PosOrder = require('equip3_pos_general.pos_order');
    const OrderWidget = PosOrder.OrderWidget;

    const EmenuOrderWidgetExt = (OrderWidget) =>
     class extends OrderWidget {
        constructor() {
            super(...arguments);
        }

        emenuShowReceipt(order){
            const printers = this.env.pos.printers;
            const receipt_template = this.env.pos.get_receipt_template();

            for (let i = 0; i < printers.length; i++) {
                let changes = order.computeChanges(printers[i].config.product_categories_ids);
                order.saved_resume = order.build_line_resume();
                order.trigger('change', order);
                if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    let orderReceipt = order.buildReceiptKitchen(changes);
                    let receipt_html = QWeb.render('OrderChangeReceipt', {
                        changes: { ...orderReceipt, ...{receipt_template}, ...{'receipt_type': 'dine-in', 'company': this.env.pos.company} },
                        widget: order
                    });
                    let report_xml = QWeb.render('KitchenReceiptXml', {
                        changes: orderReceipt,
                        widget: order
                    });
                    this.showScreen('ReportScreen', {
                        report_html: receipt_html,
                        report_xml: report_xml,
                        orderReceipt:orderReceipt
                    });
                    if ((order.syncing == false || !order.syncing) && this.env.pos.pos_bus && !this.env.pos.splitbill) {
                        this.env.pos.pos_bus.requests_printers.push({
                            action: 'request_printer',
                            data: {
                                uid: order.uid,
                                computeChanges: orderReceipt,
                            },
                            order_uid: order.uid,
                        })
                    }
                }
            }
            return true;
        }

        emenuSentToKOT(order){
            order.take_away_order = false; //Set take_away_order to False if Order Button is clicked.
            this.emenuShowReceipt(order);
            if (order && order.hasChangesToPrint() && this.env.pos.proxy.printer && this.env.pos.config.proxy_ip) {
                order.saveChanges();
            } else {
                if (!order.hasChangesToPrint()) {
                    this.env.pos.chrome.showNotification(this.env._t('Alert'), this.env._t('Have not any Lines in Cart need send to Kitchen Screen or Printers'))
                }
            }
        }

        async emenuValidateOrder(order) {
            this.pos_sync_session_order.state = 'connecting';
            let result = await this.rpc({
                model: 'pos.emenu.order',
                method: 'action_validate',
                args: [order.emenu_order_id],
            }).then(function (resp) {  return resp; });
            this.pos_sync_session_order.state = 'done';

            if(result.status == 'success'){
                order.emenu_status = 'received';
                order.trigger('change', order); // save change to local storage

                $('.o_action_manager .pos').attr('data-emenu-status','received');
            }
        }

        async onClickSyncSessionOrder() {
            super.onClickSyncSessionOrder();
            let order = this.env.pos.get_order();
            if(order.emenu_order_id){
                this.pos_sync_session_order.state = 'connecting';
                await this.env.pos.sync_emenu_order(order);
                this.pos_sync_session_order.state = 'done';

                if(order.emenu_status && order.emenu_status == 'new_order'){
                    await this.emenuValidateOrder(order);
                    await this.emenuSentToKOT(order);
                }
            }
        } 
    }

    Registries.Component.extend(OrderWidget, EmenuOrderWidgetExt);
    return OrderWidget;
});