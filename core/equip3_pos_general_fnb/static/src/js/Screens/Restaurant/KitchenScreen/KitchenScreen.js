odoo.define('equip3_pos_general_fnb.KitchenScreen', function (require) {
    'use strict';

    const KitchenScreen = require('equip3_pos_masterdata.KitchenScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');

    const KitchenScreenExt = (KitchenScreen) =>
     class extends KitchenScreen {
        constructor() {
            super(...arguments)

            useListener('click-doneComboLine', this.doneComboLine);
        } 

        doneComboLine(event) { 
            let {line, option, order} = event.detail;
            option.kot_checked = true;

            let checked = line.pos_combo_options.filter((r)=>r.kot_checked == true);
            if(line.pos_combo_options.length == checked.length){
                console.log('########## All Combo Option Done ##########')
                if (!order.ready_transfer_items) {
                    order.ready_transfer_items = 0
                }
                if (['New', 'Priority', 'Paid'].includes(line.state)) {
                    line.state = 'Ready Transfer'
                    line.state = 'Done'
                    order.ready_transfer_items += line.qty_requested
                    order.state = 'Ready Transfer'
                }
            }

            this.removeAnotherLineTheSameOrderAndProduct(line)
            this.saveOrderReceipts()
            this.env.pos.pos_bus.sync_receipt(order)
            let do_not_dlt_ticket = false
            order.new.forEach(l => {
                if(l.state != 'Done'){
                    do_not_dlt_ticket = true
                }
            })
            if(!do_not_dlt_ticket){
                this.deliveryAll(event)
            }

        }
    }

    Registries.Component.extend(KitchenScreen, KitchenScreenExt);
    return KitchenScreenExt;

});