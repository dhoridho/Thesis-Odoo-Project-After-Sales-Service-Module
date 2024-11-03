odoo.define('equip3_pos_general_fnb.BigData', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosProductTemplate = require('equip3_pos_masterdata.PosProductTemplate')
    const field_utils = require('web.field_utils');
    const core = require('web.core');
    const {Gui} = require('point_of_sale.Gui')
    const _t = core._t;
    var SuperOrder = models.Order;
    var SuperOrderline = models.Orderline;

    models.load_fields("product.template", ['is_product_bom', 'pos_bom_id', 'is_combo_product_new','pos_combo_ids']);
    models.load_fields("product.product", ['is_product_bom', 'pos_bom_id', 'is_combo_product_new','pos_combo_ids']);
    models.load_fields('restaurant.table', ['guest']);
    
    models.load_models([
        {
            model: 'mrp.bom.line',
            fields: ['id', 'bom_id','product_id','product_tmpl_id','product_qty','is_extra','additional_cost','is_configure_components','is_configurable'],
            domain: function(self) {
                return [['bom_id.is_pos_bom','=',true]];
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, records) {
                self.saveMrpBomLine(records);
            },
        }, 
        {
            model: 'pos.combo',
            fields: ['id', 'name','product_tmpl_id','maximum_pick','required','option_ids'],
            domain: function(self) {
                return [];
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, records) {
                self.savePosCombo(records);
            },
        }, 
        {
            model: 'pos.combo.option',
            fields: ['id', 'pos_combo_id','product_id','extra_price','pos_bom_line_ids', 'is_configure_components','uom_id'],
            domain: function(self) {
                return [];
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, records) {
                self.savePosComboOption(records);
            },
        }, 

    ], {'after': 'product.product'});

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);

            let pos_order_line_object = this.get_model('pos.order.line');
            if (pos_order_line_object) {
                pos_order_line_object.fields.push('pos_combo_options','bom_components');
            }
            
        },

        saveMrpBomLine(records) { 
            this.db.save_pos_bom_line(records);
        },
        savePosCombo(records) { 
            this.db.save_pos_combo(records);
        },
        savePosComboOption(records) { 
            this.db.save_pos_combo_option(records);
        },

    });


    models.Orderline = models.Orderline.extend({
        initialize: function (attributes, options) {
            let res = SuperOrderline.prototype.initialize.apply(this, arguments);
            if (!options.json) {
                this.bom_components = '';
                this.pos_combo_options = '';
            }
            return res;
        }, 

        init_from_JSON: function (json) {
            SuperOrderline.prototype.init_from_JSON.apply(this, arguments);
            if (json.bom_components) {
                this.bom_components = json.bom_components;
            }

            if (json.pos_combo_options) {
                this.pos_combo_options = json.pos_combo_options;
            }
        },

        export_as_JSON: function () {
            let json = SuperOrderline.prototype.export_as_JSON.apply(this, arguments);
            if (this.bom_components) {
                json.bom_components = this.bom_components;
            } 
            
            if (this.pos_combo_options) {
                json.pos_combo_options = this.pos_combo_options;
            } 
            return json;
        },

        bom_combo_display_name(rec){
            let self = this;
            let display_name = rec.product_id[1];
            if(self.pos.config && self.pos.config.display_product_name_without_product_code){
                return display_name.replace(/[\[].*?[\]] */, '');
            }
            return display_name;
        },
        get_bom_components_display: function () {
            let html = '';
            //Show extra components if exist
            let components = this.bom_components;
            if(components){
                components.sort(function(a, b){ return b.is_extra?1:-1; });
                for (var i = components.length - 1; i >= 0; i--) {
                    let com = components[i];
                    let label = this.bom_combo_display_name(com);
                    if(com.is_extra){
                        if(com.checked){
                            html += ' <div class="extra-component">Extra ' + label + '</div> ';
                        }
                    }else{
                        if(!com.checked){
                            html += ' <div class="extra-component">No ' + label + '</div> ';
                        }
                    }
                }
            }
            return html;
        },
        
        get_pos_combo_options_display: function () {
            let html = '';
            let combo_options = this.pos_combo_options;

            if(combo_options){
                for (var i = combo_options.length - 1; i >= 0; i--) {
                    let option = combo_options[i];
                    let label = this.bom_combo_display_name(option);
                    html += ' <div class="combo-option"><span>+ ' + label + '</span>';
                    if(option.bom_components){
                        html += '<div class="edit-bom-components"><i class="fa fa-edit"></i></div>';
                    }
                    html += '</div> ';
                }
            }
            return html;
        },

        confirm_combo_and_bom_product: async function () {
            let self = this;
            let product = this.product;

            //BoM Product
            if(product && product.pos_bom_id){
                let components = self.pos.db.get_pos_bom_components(product);
                let customize_bom = self.pos.config.customize_bom;
                let is_configure_components = components.length!=0?components[0].is_configure_components:false;
                let add_values = {};
                if(is_configure_components && customize_bom){
                    let {confirmed, payload: values} = await Gui.showPopup('CustomizeBomPopUps', {
                        title: product.display_name.replace(/[\[].*?[\]] */, ''),
                        components: components,
                    });
                    if(confirmed){
                        add_values['bom_components'] = values['components'];
                        add_values['notes'] = values['notes'];
                    }
                }else{
                    let _components = [];
                    for (var i = components.length - 1; i >= 0; i--) {
                        if(!components[i].is_extra){
                            let com = components[i];
                            _components.push({
                                additional_cost: com.additional_cost,
                                bom_id: com.bom_id,
                                id: com.id,
                                is_extra: com.is_extra,
                                product_id: com.product_id,
                                product_qty: com.product_qty,
                                product_tmpl_id: com.product_tmpl_id,
                                checked: true,
                            });
                        }
                    }
                    add_values['bom_components'] = _components;
                }

                let selectedLine = this;
                if(add_values.bom_components && typeof add_values.bom_components != 'undefined' && add_values.bom_components.length){
                    selectedLine.bom_components = add_values.bom_components;
                    if(add_values.notes){
                        selectedLine.set_note(add_values.notes);
                    }
                    return true;
                }
            }

            // Combo Product New
            if(product && product.is_combo_product_new){
                if(!product.pos_bom_id){
                    let add_values = {};
                    let {confirmed, payload: values} = await Gui.showPopup('ComboOptionPopUps', {
                        title: product.display_name.replace(/[\[].*?[\]] */, ''),
                        combo: self.pos.db.get_pos_combo_product(product),
                    });
                    if(confirmed){
                        add_values['pos_combo_options'] = values['combo_options'];
                    }
                    let selectedLine = this;
                    if(add_values.pos_combo_options && typeof add_values.pos_combo_options != 'undefined' && add_values.pos_combo_options.length){
                        selectedLine.pos_combo_options = add_values.pos_combo_options;
                        return true;
                    }
                }
            }

            return false;
        },

        get_additional_cost: function(){
            let additional_cost = SuperOrderline.prototype.get_additional_cost.apply(this, arguments);
            if(this.bom_components){
                for (let component of this.bom_components){
                    if(component.checked && component.is_extra && component.additional_cost){
                        additional_cost += component.additional_cost;
                    }
                }
            }
            if(this.pos_combo_options){
                for (let combo_option of this.pos_combo_options){
                    if(combo_option.extra_price != 0){
                        additional_cost += combo_option.extra_price;
                    }
                    if(combo_option.bom_components){
                        for (let component of combo_option.bom_components){
                            if(component.checked && component.is_extra && component.additional_cost){
                                additional_cost += component.additional_cost;
                            }
                        }
                    }
                }
            }
            return additional_cost;
        },

        get_additional_cost_x_quantity: function(){
            let additional_cost = SuperOrderline.prototype.get_additional_cost_x_quantity.apply(this, arguments);
            if(this.bom_components){
                for (let component of this.bom_components){
                    if(component.checked && component.is_extra && component.additional_cost){
                        additional_cost += component.additional_cost * this.quantity;
                    }
                }
            }
            if(this.pos_combo_options){
                for (let combo_option of this.pos_combo_options){
                    if(combo_option.extra_price != 0){
                        additional_cost += combo_option.extra_price * this.quantity;
                    }
                    if(combo_option.bom_components){
                        for (let component of combo_option.bom_components){
                            if(component.checked && component.is_extra && component.additional_cost){
                                additional_cost += component.additional_cost * this.quantity;
                            }
                        }
                    }
                }
            }
            return additional_cost;
        },
        

    });
});


