odoo.define('equip3_pos_masterdata.SubmitOrderButton', function (require) {
    'use strict';

    const SubmitOrderButton = require('pos_restaurant.SubmitOrderButton');
    SubmitOrderButton.template = 'RetailSubmitOrderButton'
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const core = require('web.core');
    const QWeb = core.qweb;
    const {useState} = owl;

    const RetailSubmitOrderButton = (SubmitOrderButton) =>
        class extends SubmitOrderButton {
            constructor() {
                super(...arguments);

                this.state = useState({ sync: '' });
            }

            showReceipt() {
                const printers = this.env.pos.printers;
                const selectedOrder = this.env.pos.get_order();
                const receipt_template = this.env.pos.get_receipt_template();

                for (let i = 0; i < printers.length; i++) {
                    let changes = selectedOrder.computeChanges(printers[i].config.product_categories_ids);
                    selectedOrder.saved_resume = selectedOrder.build_line_resume();
                    selectedOrder.trigger('change', selectedOrder);
                    if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                        let orderReceipt = selectedOrder.buildReceiptKitchen(changes);
                        let receipt_html = QWeb.render('OrderChangeReceipt', {
                            changes: { ...orderReceipt, ...{receipt_template}, ...{'receipt_type': 'dine-in', 'company': this.env.pos.company} },
                            widget: selectedOrder
                        });
                        let report_xml = QWeb.render('KitchenReceiptXml', {
                            changes: orderReceipt,
                            widget: selectedOrder
                        });
                        this.showScreen('ReportScreen', {
                            report_html: receipt_html,
                            report_xml: report_xml,
                            orderReceipt:orderReceipt
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

            get addedClasses() {
                let classElement = super.addedClasses
                if (!this._currentOrder) return classElement;
                const changes = this._currentOrder.hasChangesToPrint();
                return classElement
            }

            async beforeShowReceipt() {
                return Promise.resolve(true);
            }

            async onClick() {
                const order = this.env.pos.get_order();
                //Set take_away_order to False if Order Button is clicked.
                order.take_away_order = false;
                await this.beforeShowReceipt();
                this.showReceipt()
                if (order && order.hasChangesToPrint() && this.env.pos.proxy.printer && this.env.pos.config.proxy_ip) {
                    order.saveChanges();
                } else {
                    if (!order.hasChangesToPrint()) {
                        this.env.pos.chrome.showNotification(this.env._t('Alert'), this.env._t('Have not any Lines in Cart need send to Kitchen Screen or Printers'))
                    }
                    super.onClick()
                }

            }

            get countItemsNeedPrint() {
                const selectedOrder = this.env.pos.get_order();
                if (!selectedOrder) {
                    return 0
                }
                let countItemsNeedToPrint = 0
                let printers = this.env.pos.printers;
                for (let i = 0; i < printers.length; i++) {
                    let changes = selectedOrder.computeChanges(printers[i].config.product_categories_ids);
                    if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                        countItemsNeedToPrint += changes['new'].length
                        countItemsNeedToPrint += changes['cancelled'].length
                    }
                }
                return countItemsNeedToPrint
            }
        }
    ProductScreen.controlButtons = ProductScreen.controlButtons.filter((ar)=> ar.name != 'SubmitOrderButton');
    Registries.Component.extend(SubmitOrderButton, RetailSubmitOrderButton);

    return RetailSubmitOrderButton;
});