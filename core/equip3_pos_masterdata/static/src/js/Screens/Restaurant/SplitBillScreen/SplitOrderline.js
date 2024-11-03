odoo.define('equip3_pos_masterdata.SplitOrderline', function (require) {
    'use strict';

    const SplitOrderline = require('pos_restaurant.SplitOrderline');
    const Registries = require('point_of_sale.Registries');

    const RetailSplitOrderline = (SplitOrderline) =>
        class extends SplitOrderline {
            get isSelected() {
                // return this.props.split.checkmark
                return false
            }

            checkbox_line(){
                if(this.props.split.checkmark)
                {this.props.split.checkmark = false}
                else{
                    this.props.split.checkmark = true
                }
            }
   
            onClick() {
                
            }

            add_qty(){
                if (this.props.split.quantity<this.props.split.max_qty) {
                    this.props.split.quantity += 1 
                }
            }
            min_qty(){
                if (this.props.split.quantity>1) {
                    this.props.split.quantity -= 1 
                }
                    
            }
    
        }
    Registries.Component.extend(SplitOrderline, RetailSplitOrderline);

    return RetailSplitOrderline;
});
