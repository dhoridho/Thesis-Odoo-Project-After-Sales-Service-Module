odoo.define('equip3_pos_general_fnb.DefaultResScreen', function (require) {
    'use strict';

    const DefaultResScreen = require('equip3_pos_masterdata.DefaultResScreen');
    const Registries = require('point_of_sale.Registries');

    const DefaultResScreenExt = (DefaultResScreen) =>
     class extends DefaultResScreen {
        constructor() {
            super(...arguments)
        }
        
        showFS() {
            if (this.env.pos.config.iface_floorplan) {
                const table = this.env.pos.table;
                this.env.pos.selected_order_method = 'dine-in';
                $('body').attr('data-ems',"0")
                jQuery('.back-to-home').show();
                // click()
                jQuery('.pos').attr('data-selected-order-method','dine-in');
                jQuery('.pos > .pos-content').attr('data-selected-order-method','dine-in');
                this.showScreen('FloorScreen',{ floor: table ? table.floor : null, selected_order_method: 'dine-in' })
            } else {
                $('body').attr('data-ems',"0")
                return super.startScreen;
            }
        }
        
        showFS1() {
            $('body').attr('data-ems',"0")
            jQuery('.back-to-home').show();
            jQuery('.pos').attr('data-selected-order-method','dine-in');  
            jQuery('.pos > .pos-content').attr('data-selected-order-method','dine-in');
            this.showScreen('ProductScreen', {
                selected_order_method: 'dine-in', 
            });
            jQuery('.pos-topheader .back-to-home').addClass('hm_button_show').removeClass('hm_button_hidden'); 
            return super.startScreen
        }

        showTAS() {
            if(this.env.pos.selected_order_method != 'takeaway'){
                this.clearCart();
            }
            
            if(this.env.pos.tables) {
                var table = this.env.pos.tables[0]
            }

            $('body').attr('data-ems',"0")
            
            if(this.env.pos.tables) {
                this.env.pos.set_table(table)
            }

            jQuery('.buttton_split_table').addClass('hm_button_hidden');
            $('.buttton_split_table').attr('display',"none");

            this.env.pos.selected_order_method = 'takeaway';
            jQuery('.back-to-home').show();
            jQuery('.pos').attr('data-selected-order-method','takeaway');  
            jQuery('.pos > .pos-content').attr('data-selected-order-method','takeaway');  
            this.showScreen('ProductScreen', {selected_order_method: 'takeaway'});
        }

        //employee meal function
        showEMS() {
            if(this.env.pos.selected_order_method != 'employee-meal'){
                this.clearCart();
            }

            console.log('this.env.pos:::::', this.env.pos)
            
            //sync remaining employee budget            
            this.env.pos.getEmployeeMeals();

            if(this.env.pos.tables) {
                var table = this.env.pos.tables[0]
            }

            $('body').attr('data-ems',"1");

            if(this.env.pos.tables) {
                this.env.pos.set_table(table)
            }

            this.env.pos.selected_order_method = 'employee-meal';
            jQuery('.back-to-home').show();
            jQuery('.pos').attr('data-selected-order-method','employee-meal');  
            jQuery('.pos > .pos-content').attr('data-selected-order-method','employee-meal');  
            this.showScreen('ProductScreen', {
                selected_order_method: 'employee-meal', 
                employee_meal: 1,
            });
        }
        
    }

    Registries.Component.extend(DefaultResScreen, DefaultResScreenExt);
    return DefaultResScreenExt;

});