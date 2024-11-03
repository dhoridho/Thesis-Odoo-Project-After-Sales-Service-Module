odoo.define('equip3_pos_general_fnb.fire_maincourse_button', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const _t = core._t;
    const {Gui} = require('point_of_sale.Gui');
    const {useState} = owl;

    class  FireMaincourseButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        async click() {
            let self = this;
            const selectedOrder = this.env.pos.get_order();
            let kitchenReceiptOrders = this.env.pos.db.getOrderReceipts();
            let existing_receipt = kitchenReceiptOrders.find(r => r.uid == selectedOrder.uid);
            if(existing_receipt){
                const printers = this.env.pos.printers;
                let categ_ids = this.env.pos.config.fire_main_course;
                for (let i = 0; i < printers.length; i++) {
                    let changes = selectedOrder.computeChanges(printers[i].config.product_categories_ids);
                    selectedOrder.saved_resume = selectedOrder.build_line_resume_for_fire_dining(categ_ids);
                    selectedOrder.trigger('change', selectedOrder);  
                    if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                        changes['fire_main_course'] = true;

                        let newLine = [];
                        changes.new.forEach(function(item, index, object) {
                            var product = self.env.pos.db.get_product_by_id(item.product_id);
                            let pos_categ_id = product.pos_categ_id[0];
                            if(categ_ids.includes(pos_categ_id)){
                                newLine.push(item);
                            }
                        });
                        changes['new'] = newLine;
                        let receipt = selectedOrder.buildReceiptKitchen(changes);
                        if ((selectedOrder.syncing == false || !selectedOrder.syncing) && this.env.pos.pos_bus && !this.env.pos.splitbill) {
                            this.env.pos.pos_bus.requests_printers.push({
                                action: 'request_printer',
                                data: {
                                    uid: selectedOrder.uid,
                                    computeChanges: receipt,
                                },
                                order_uid: selectedOrder.uid,
                            });
                        }
                    }
                }
                
                this.env.pos.alert_message({
                    title: this.env._t('Warning'),
                    body: this.env._t('Main Course has been sent to the KOT')
                });

            }
        } 
    }

    FireMaincourseButton.template = 'FireMaincourseButton';
    Registries.Component.add(FireMaincourseButton);
    return FireMaincourseButton;
});
