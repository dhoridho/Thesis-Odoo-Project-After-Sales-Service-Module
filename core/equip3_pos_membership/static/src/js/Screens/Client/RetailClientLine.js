odoo.define('equip3_pos_membership.RetailClientLine', function (require) {
    'use strict';

    const RetailClientLine = require('point_of_sale.ClientLine');
    const Registries = require('point_of_sale.Registries');

    const PosMemRetailClientLine = (RetailClientLine) =>
        class extends RetailClientLine {
            constructor() {
                super(...arguments);
            } 

            // get addClass() {
            //     let values = super.addClass;
            //     let config_pos_branch_id = false;
            //     if(this.env.pos.config.pos_branch_id){
            //         config_pos_branch_id = this.env.pos.config.pos_branch_id[0];
            //     }
            //     let partner = this.props.partner;
            //     if(partner){
            //         let is_hidden = true;
            //         if(partner.is_pos_member){
            //             if(typeof partner.pos_branch_id !== undefined){
            //                 if(partner.pos_branch_id == false || partner.pos_branch_id[0] == config_pos_branch_id){
            //                     is_hidden = false;
            //                 }
            //             }
            //         }
            //         if(partner.removed){
            //             is_hidden = true;
            //         }
            //         values['oe_hidden'] = is_hidden;
            //     }
            //     return values;
            // } 

        }

        
    Registries.Component.extend(RetailClientLine, PosMemRetailClientLine);
    return PosMemRetailClientLine;
});
