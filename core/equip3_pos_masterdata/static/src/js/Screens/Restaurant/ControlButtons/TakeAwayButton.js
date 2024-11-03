odoo.define('equip3_pos_masterdata.TakeAwayButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const QWeb = core.qweb;
    const {useState} = owl;

    /**
     * IMPROVEMENT: Perhaps this class is quite complicated for its worth.
     * This is because it needs to listen to changes to the current order.
     * Also, the current order changes when the selectedOrder in pos is changed.
     * After setting new current order, we update the listeners.
     */
    class TakeAwayButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
            this._currentOrder.orderlines.on('change', this.render, this);
            this.env.pos.on('change:selectedOrder', this._updateCurrentOrder, this);

            this.state = useState({ sync: '' });
        }

        willUnmount() {
            this._currentOrder.orderlines.off('change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
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

                    changes['take_away_order'] = true
                    changes['take_away_tiket_no'] = this.env.pos.db.getTakeAwayTicketOrderNumber();

                    let orderReceipt = selectedOrder.buildReceiptKitchen(changes);

                    let receipt_html = QWeb.render('OrderChangeReceipt', {
                        changes: { ...orderReceipt, ...{receipt_template}, ...{'receipt_type': 'takeaway', 'company': this.env.pos.company} },
                        widget: selectedOrder
                    });
                    let report_xml = QWeb.render('KitchenReceiptXml', {
                        changes: orderReceipt,
                        widget: selectedOrder
                    });
                    //Open Report Screen after the take away button clicked
                    this.showScreen('ReportScreen', {
                        report_html: receipt_html,
                        report_xml: report_xml,
                        orderReceipt:orderReceipt,
                        TakeAway:true,
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

        async beforeShowReceipt() {
            return Promise.resolve(true);
        }

        async onClick() {
            const order = this.env.pos.get_order();
            if (order.hasChangesToPrint()) {
                order.take_away_order = true; 
                await this.beforeShowReceipt();
                this.showReceipt();
                order.saveChanges();
            }
        }

        get addedClasses() {
            if (!this._currentOrder) return {};
            const changes = this._currentOrder.hasChangesToPrint();
            const skipped = changes ? false : this._currentOrder.hasSkippedChanges();
            return {
                highlight: changes,
                altlight: skipped,
            };
        }

        _updateCurrentOrder(pos, newSelectedOrder) {
            this._currentOrder.orderlines.off('change', null, this);
            if (newSelectedOrder) {
                this._currentOrder = newSelectedOrder;
                this._currentOrder.orderlines.on('change', this.render, this);
            }
        }

        get countItemsNeedPrint() {
            let selectedOrder = this.env.pos.get_order();
            if (!selectedOrder) {
                return 0
            }
            let countItemsNeedToPrint = 0
            var printers = this.env.pos.printers;
            for (var i = 0; i < printers.length; i++) {
                var changes = selectedOrder.computeChanges(printers[i].config.product_categories_ids);
                if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    countItemsNeedToPrint += changes['new'].length
                    countItemsNeedToPrint += changes['cancelled'].length
                }
            }
            return countItemsNeedToPrint
        }
    }

    TakeAwayButton.template = 'TakeAwayButton';

    ProductScreen.addControlButton({
        component: TakeAwayButton,
        condition: function () {
            return this.env.pos.config.screen_type != 'kitchen' && this.env.pos.config.sync_multi_session && this.env.pos.config.takeaway_order;
        },
        position: ['after', 'SubmitOrderButton'],
    });

    Registries.Component.add(TakeAwayButton);

    return TakeAwayButton;
});
