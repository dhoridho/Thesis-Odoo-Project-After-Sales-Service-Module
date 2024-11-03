odoo.define('equip3_pos_membership.database', function (require) {
    const PosDB = require('point_of_sale.DB');
    const _super_db = PosDB.prototype;
    const _super_init_ = PosDB.prototype.init;
    const utils = require('web.utils');
    const round_pr = utils.round_precision;

    var _super_add_partners_ = PosDB.prototype.add_partners;
    PosDB.prototype.add_partners = function(partners) {
        let partner;
        for (let i = 0, len = partners.length; i < len; i++) {
            partner = partners[i];
            if (partner.pos_loyalty_point) {
                partners[i].pos_loyalty_point = round_pr(partner.pos_loyalty_point, window.posmodel.currency.rounding);
            }
            if (partner.pos_loyalty_type) {
                partners[i].pos_loyalty_type_name = partner.pos_loyalty_type[1];
            }
        }
        _super_add_partners_.call(this, partners);
    };


    var _super_filter_add_partners_ = PosDB.prototype.filter_add_partners;
    PosDB.prototype.filter_add_partners = function(partners) {
        let config_pos_branch_id = false;
        if(window.posmodel.config.pos_branch_id){
            config_pos_branch_id = window.posmodel.config.pos_branch_id[0];
        }
        partners = partners.filter(function(c){
            let is_same_branch = !c.pos_branch_id;
            if(c.pos_branch_id && c.pos_branch_id[0] == config_pos_branch_id){
                is_same_branch = true;
            }
            if(c.is_pos_member && is_same_branch){
                return true;
            }
            if(c.removed){
                return false;
            }
            return false;
        });
        let res = _super_filter_add_partners_.call(this, partners);
        return res;
    };
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);
        
        // TODO: stored customer.deposit/member deposit
        this.customer_deposit_last_write_date = null;
        this.customer_deposit_by_id = {};
        this.customer_deposit_string = '';
        this.customer_deposit_string_by_id = {};
        this.customer_deposit_search_string_by_id = {};
        this.customer_deposit_disable_partner_ids = [];
    };
    
    PosDB.include({

        get_customer_deposits: function (max_count) {
            let deposits = [];
            let max = 0;
            for (let res_id in this.customer_deposit_by_id) {
                let deposit = this.customer_deposit_by_id[res_id];
                deposits.push(deposit);
                max += 1;
                if (max_count > 0 && max >= max_count) {
                    break;
                }
            }
            return deposits;
        },

        get_customer_deposit_by_partner_id: function (partner_id) {
            let value = null;
            for (let res_id in this.customer_deposit_by_id) {
                let deposit = this.customer_deposit_by_id[res_id];
                if(deposit.partner_id[0] == partner_id){
                    if(['post'].includes(deposit.state) == true){
                        value = deposit;
                        break;
                    }
                }
            }
            return value;
        },

        _customer_deposits_search_string: function (data) {
            let str = data.name;
            if(data.partner_id){
                str += '|' + data.partner_id[1];
            }
            if(data.deposit_account_id){
                str += '|' + data.deposit_account_id[1];
            }
            return '' + data['id'] + ':' + str.replace(':', '') + '\n';
        },

        save_customer_deposits: function (datas) {
            for (let i = 0; i < datas.length; i++) {
                let data = datas[i];
                let partner_id = data.partner_id;
                let state = data.state;
                let label = this._customer_deposits_search_string(data);
                this.customer_deposit_by_id[data.id] = data;
                this.customer_deposit_string_by_id[data.id] = label;
                this.customer_deposit_search_string_by_id[data.id] = label;

                if(['draft', 'post'].includes(state)){
                    if(this.customer_deposit_disable_partner_ids.includes(partner_id[0]) == false){
                        this.customer_deposit_disable_partner_ids.push(partner_id[0]);
                    }
                }

                if(!this.customer_deposit_last_write_date){
                    this.customer_deposit_last_write_date = data.write_date;
                }else{
                    if (this.customer_deposit_last_write_date != data.write_date && new Date(this.customer_deposit_last_write_date).getTime() < new Date(data.write_date).getTime()) {
                        this.customer_deposit_last_write_date = data.write_date;
                        if(!data.write_date){
                            console.warn('[customer_deposit_last_write_date] write_date is undefined.');
                        }
                    } 
                }
            }
            for (let res_id in this.customer_deposit_search_string_by_id) {
                this.customer_deposit_string += this.customer_deposit_search_string_by_id[res_id];
            }
        },

        search_customer_deposits: function (query) {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
            query = query.replace(' ', '.+');
            const re = RegExp("([0-9]+):.*?" + query, "gi");
            let deposits = [];
            let deposit_ids = [];
            for (let i = 0; i < this.limit; i++) {
                let r = re.exec(this.customer_deposit_string);
                if (r && r[1]) {
                    let id = r[1];
                    if (this.customer_deposit_by_id[id] !== undefined && !deposit_ids.includes(id)) {
                        deposits.push(this.customer_deposit_by_id[id]);
                        deposit_ids.push(id);
                    }
                } else {
                    break;
                }
            }
            return deposits;
        },
    });

}); 