odoo.define('equip3_pos_general_fnb.FloorScreen', function(require) {
    'use strict';

    const FloorScreen = require('pos_restaurant.FloorScreen');
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;

    const POSFloorScreen = (FloorScreen) =>
        class extends FloorScreen {

            // Overide
            async _onSelectTable(event) {
                
                const table = event.detail;
                if (this.state.isEditMode) {
                    this.state.selectedTableId = table.id;
                } else {
                    this.env.pos.set_table(table);
                }

                if(!this.state.isEditMode){
                    if(this.env.pos.config.is_manual_sync_for_sync_between_session){
                        //TODO: check and sync session order when select table
                        let selectedOrder = this.env.pos.get_order();
                        if(selectedOrder){
                            if(selectedOrder.sync_write_date){
                                await this.env.pos.sync_session_order(selectedOrder);
                            }
                        }
                    }
                    
                    if($(event.target).data('bs.popover') != undefined){
                        $(event.target).popover('hide');
                    }
                }
            }

        };
    Registries.Component.extend(FloorScreen, POSFloorScreen);

    return FloorScreen;
});
