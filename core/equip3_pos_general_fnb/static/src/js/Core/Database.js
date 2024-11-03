odoo.define('equip3_pos_general_fnb.Database', function (require) {
    'use strict';

    var PosDB = require('point_of_sale.DB'); 
    var _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);
        
        // TODO: stored mrp.bom.line
        this.pos_bom_line = {};

        // TODO: stored pos.combo & pos.combo.line
        this.pos_combo_by_id = {};
        this.pos_combo_option_by_id = {};
    };
    
    PosDB.include({

        save_pos_bom_line: function (records) {
            for (let record of records){
                if(record['product_id']){
                    let product_display_name = record['product_id'][1];
                    record['full_product_name'] = product_display_name;
                    record['product_only_name'] =  product_display_name.replace(/[\[].*?[\]] */, '');
                }
            }
            this.pos_bom_line = records;
        },
        get_pos_bom_components: function(product){
            let components = [];
            if(product.pos_bom_id){
                for (var i = this.pos_bom_line.length - 1; i >= 0; i--) {
                    let line = this.pos_bom_line[i];
                    if(line.bom_id[0] == product.pos_bom_id[0]){
                        components.push(line);
                    }
                }
            }
            components.sort(function(a, b){ return b.is_extra?-1:1; });
            return components;
        },
        get_pos_bom_component_by_ids: function(ids){
            let components = [];
            for (var i = this.pos_bom_line.length - 1; i >= 0; i--) {
                let line = this.pos_bom_line[i];
                if(ids.includes(line.id) == true){
                    components.push(line);
                }
            }
            components.sort(function(a, b){ return b.is_extra?-1:1; });
            return components;
        },

        save_pos_combo: function (records) {
            for (let record of records){
                if(record['product_tmpl_id']){
                    let product_display_name = record['product_tmpl_id'][1];
                    record['full_product_name'] = product_display_name;
                    record['product_only_name'] =  product_display_name.replace(/[\[].*?[\]] */, '');
                }
                this.pos_combo_by_id[record.id] = record;
            }
        },
        save_pos_combo_option: function (records) {
            for (let record of records){
                if(record['product_id']){
                    let product_display_name = record['product_id'][1];
                    record['full_product_name'] = product_display_name;
                    record['product_only_name'] =  product_display_name.replace(/[\[].*?[\]] */, '');
                }
            }
            for (var i = records.length - 1; i >= 0; i--) {
                this.pos_combo_option_by_id[records[i].id] = records[i];
            }
            for(let i in this.pos_combo_by_id){
               this.pos_combo_by_id[i].options = records.filter( (r)=>this.pos_combo_by_id[i].option_ids.includes(r.id) );
            }
        },
        get_pos_combo_product: function(product){
            let lines = [];
            if(product.pos_combo_ids){
                for(let combo_id of product.pos_combo_ids){
                    let combo = this.pos_combo_by_id[combo_id];
                    if(combo){
                        lines.push(combo);
                    }
                }
            }
            return lines;
        }


    });
});