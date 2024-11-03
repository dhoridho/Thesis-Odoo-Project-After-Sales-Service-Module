odoo.define('equip3_pos_masterdata.SyncModelsButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require('web.custom_hooks');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {Gui} = require('point_of_sale.Gui');

    class SyncModelsButton extends PosComponent {
        
        constructor() {
            super(...arguments);

            useListener('sync-pos-models', () => this.onClick());
        }

        async onClick(){
            this.env.pos._check_connection();
            await Gui.showPopup('SyncModels');
        }
       
    }

    SyncModelsButton.template = 'SyncModelsButton';
    Registries.Component.add(SyncModelsButton);
    return SyncModelsButton;
});
