odoo.define('equip3_pos_order_retail.TakeAwayButton', function (require) {
    'use strict';

    const TakeAwayButton = require('pos_retail.TakeAwayButton');
    const PosComponent = require('point_of_sale.PosComponent');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const QWeb = core.qweb;

    const TakeAwayButtonExtend = (TakeAwayButton) =>
        class extends TakeAwayButton {
            constructor() {
                super(...arguments);
            }

            showReceipt() {
                const printers = this.env.pos.printers;
                const selectedOrder = this.env.pos.get_order()
                for (let i = 0; i < printers.length; i++) {
                    let changes = selectedOrder.computeChanges(printers[i].config.product_categories_ids);
                    if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                        selectedOrder.take_away_order = true;
                        let orderReceipt = selectedOrder.buildReceiptKitchen(changes);
                        orderReceipt['take_away_order'] = true
                        let receipt_html = QWeb.render('OrderChangeReceipt', {
                            changes: orderReceipt,
                            widget: selectedOrder
                        });
                        let report_xml = QWeb.render('KitchenReceiptXml', {
                            changes: orderReceipt,
                            widget: selectedOrder
                        });
                        this.showScreen('ReportScreen', {
                            report_html: receipt_html,
                            report_xml: report_xml,
                        });
                        if ((selectedOrder.syncing == false || !selectedOrder.syncing) && this.env.pos.pos_bus && !this.env.pos.splitbill) {
                            this.env.pos.pos_bus.requests_printers.push({
                                action: 'request_printer',
                                data: {
                                    uid: selectedOrder.uid,
                                    computeChanges: orderReceipt,
                                },
                                order_uid: selectedOrder.uid,
                            })
                        }
                    }
                }
                return true;
            }

            async onClick() {
                const order = this.env.pos.get_order();
                this.showReceipt()
                if (order.hasChangesToPrint()) {
                    order.take_away_order = true
                    order.saveChanges();
                }else {
                    if (!order.hasChangesToPrint()) {
                        this.env.pos.chrome.showNotification(this.env._t('Alert'), this.env._t('Have not any Lines in Cart need send to Kitchen Screen or Printers'))
                    }
                    super.onClick()
                }
            }
        }

        Registries.Component.extend(TakeAwayButton, TakeAwayButtonExtend);

    return TakeAwayButton;
});
