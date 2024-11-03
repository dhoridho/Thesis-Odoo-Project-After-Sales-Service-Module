odoo.define('equip3_pos_general_fnb.KitchenOrder', function (require) {
    'use strict';

    const KitchenOrder = require('equip3_pos_masterdata.KitchenOrder');
    const Registries = require('point_of_sale.Registries');

    const KitchenOrderExt = (KitchenOrder) =>
     class extends KitchenOrder {
        constructor() {
            super(...arguments)
        } 
        
        get_pos_combo_options_values(options){
            if(!options){
                return [];
            }
            const grouped = options.reduce((group, option) => {
              const { pos_combo_id } = option;
              if(pos_combo_id){
                  group[pos_combo_id[0]] = group[pos_combo_id[0]] ?? [];
                  group[pos_combo_id[0]].push(option);
              }
              return group;
            }, {});
            return grouped;
        }
    }

    Registries.Component.extend(KitchenOrder, KitchenOrderExt);
    return KitchenOrderExt;

});