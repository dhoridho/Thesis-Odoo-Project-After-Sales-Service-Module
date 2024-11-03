odoo.define('equip3_pos_membership.SyncModels', function (require) {
    'use strict';

    const SyncModels = require('equip3_pos_masterdata.SyncModels');
    const Registries = require('point_of_sale.Registries');

    const PosMemSyncModels = (SyncModels) =>
        class extends SyncModels {
            constructor() {
                super(...arguments);
            } 

            _sync_partner_label(){
                let label = super._sync_partner_label();
                return 'Members';
            }

        }
        
    Registries.Component.extend(SyncModels, PosMemSyncModels);
    return PosMemSyncModels;
});
