odoo.define('equip3_pos_masterdata_fnb.Database', function (require) {
    'use strict';

    var PosDB = require('point_of_sale.DB'); 
    var _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);
        // TODO: store employee meal
        this.employee_meal_by_id = {};
        this.employee_meal_string = '';
        this.employee_meal_string_by_id = {};
        this.employee_meal_search_string_by_id = {};

        // TODO: stored reserve orders
        this.reserve_order_by_id = {};
        this.reserve_order_string = '';
        this.reserve_order_string_by_id = {};
        this.reserve_order_search_string_by_id = {};
    };
    
    PosDB.include({
        
        _employee_meal_search_string: function (employee) {
            let str = employee.name;
            str = '' + employee['id'] + ':' + str.replace(':', '') + '\n';
            return str;
        },

        save_employee_meal: function (employees) {
            for (let i = 0; i < employees.length; i++) {
                let employee = employees[i];
                let label = this._employee_meal_search_string(employee);
                this.employee_meal_by_id[employee.id] = employee;
                this.employee_meal_string_by_id[employee.id] = label;
                this.employee_meal_search_string_by_id[employee.id] = label;
            }
            for (let res_id in this.employee_meal_search_string_by_id) {
                this.employee_meal_string += this.employee_meal_search_string_by_id[res_id];
            }
        },
        
        get_employee_meal: function (max_count) {
            let employees = [];
            let max = 0;
            for (let res_id in this.employee_meal_by_id) {
                let employee = this.employee_meal_by_id[res_id];
                employees.push(employee);
                max += 1;
                if (max_count > 0 && max >= max_count) {
                    break;
                }
            }
            return employees;
        },
        search_employee_meal: function (query) {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
            query = query.replace(' ', '.+');
            const re = RegExp("([0-9]+):.*?" + query, "gi");
            let employees = [];
            let employee_ids = [];
            for (let i = 0; i < this.limit; i++) {
                let r = re.exec(this.employee_meal_string);
                if (r && r[1]) {
                    let id = r[1];
                    if (this.employee_meal_by_id[id] !== undefined && !employee_ids.includes(id)) {
                        employees.push(this.employee_meal_by_id[id]);
                        employee_ids.push(id);
                    }
                } else {
                    break;
                }
            }
            return employees;
        },


        _reserve_order_search_string: function (order) {
            let str = order.name;
            if (order.customer_name) {
                str += '|' + order.customer_name;
            }
            if (order.cust_phone_no) {
                str += '|' + order.cust_phone_no;
            }
            // if (order.reservation_from) {
            //     str += '|' + order.reservation_from;
            // }
            // if (order.reservation_to) {
            //     str += '|' + order.reservation_to;
            // }
            if (order.table_floor) {
                str += '|' + order.table_floor[1] ;
            }
            if (order.table_no) {
                str += '|' + order.table_no[1];
            }

            str = '' + order['id'] + ':' + str.replace(':', '') + '\n';
            return str;
        },
        save_reserve_order: function (reserve_orders) {
            for (let i = 0; i < reserve_orders.length; i++) {
                let order = reserve_orders[i];
                let label = this._reserve_order_search_string(order);
                this.reserve_order_by_id[order.id] = order;
                this.reserve_order_string_by_id[order.id] = label;
                this.reserve_order_search_string_by_id[order.id] = label;
            }
            for (let order_id in this.reserve_order_search_string_by_id) {
                this.reserve_order_string += this.reserve_order_search_string_by_id[order_id];
            }
        },
        get_reserve_order: function (max_count) {
            let orders = [];
            let max = 0;
            for (let order_id in this.reserve_order_by_id) {
                let order = this.reserve_order_by_id[order_id];
                orders.push(order);
                max += 1;
                if (max_count > 0 && max >= max_count) {
                    break;
                }
            }
            return orders;
        },
        search_reserve_order: function (query) {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
            query = query.replace(' ', '.+');
            const re = RegExp("([0-9]+):.*?" + query, "gi");
            let reserve_orders = [];
            let reserve_order_ids = []
            for (let i = 0; i < this.limit; i++) {
                let r = re.exec(this.reserve_order_string);
                if (r && r[1]) {
                    let id = r[1];
                    if (this.reserve_order_by_id[id] !== undefined && !reserve_order_ids.includes(id)) {
                        reserve_orders.push(this.reserve_order_by_id[id]);
                        reserve_order_ids.push(id)
                    }
                } else {
                    break;
                }
            }
            return reserve_orders;
        },



    });
});