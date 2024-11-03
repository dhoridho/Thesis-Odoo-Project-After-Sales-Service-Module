odoo.define('equip3_pos_masterdata_fnb.BigData', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const field_utils = require('web.field_utils');
    const core = require('web.core');
    const _t = core._t;
    var SuperOrder = models.Order;

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);
        }, 
        saveEmployeeMeals(employees) {
            if (!this.employee_meal_ids) {
                this.employee_meal_ids = [];
            }
            for (let i = 0; i < employees.length; i++) {
                let employee = employees[i]
                if (!this.employee_meal_ids.includes(employee.id)) {
                    this.employee_meal_ids.push(employee.id)
                } 
                for (let j = this.employee_meal_ids.length - 1; j >= 0; j--) {
                    if(employee.id == this.employee_meal_ids[j].id){
                        this.employee_meal_ids[j].remaining_budget = employee.remaining_budget;
                        break;
                    }
                }
            }
            this.db.save_employee_meal(employees);
        },
        async getEmployeeMeals() {
            const self = this;
            let domain = [['remaining_budget','>',0]];
            const model = self.get_model('hr.employee');
            const params = {
                model: 'hr.employee',
                fields: [
                    'id',
                    'name',
                    'remaining_budget'
                ],
                domain: domain,
                context: {
                    'pos_config_id': self.config.id
                }
            }
            let employees = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']);
            this.saveEmployeeMeals(employees);

            this.alert_message({
                title: _t('Syncing'),
                body: _t('Employee Meal')
            });
        },


        
        saveReserveOrders(orders) {
            if (!this.reserve_order_ids) {
                this.reserve_order_ids = [];
            }
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i]
                if (!this.reserve_order_ids.includes(order.id)) {
                    this.reserve_order_ids.push(order.id)
                } 

                order.reservation_from = field_utils.format.datetime(
                    field_utils.parse.datetime(order.reservation_from));
                
                order.reservation_to = field_utils.format.datetime(
                    field_utils.parse.datetime(order.reservation_to));
            }
            this.db.save_reserve_order(orders);
        },
        async getReserveOrders() {
            this.alert_message({
                title: _t('Syncing'),
                body: _t('Reserve Orders')
            })
            const self = this;
            let domain = [
                ['reservation_from','>=', moment().format('YYYY-MM-DD') + ' 00:00:00'], 
                ['reservation_from','<=', moment().format('YYYY-MM-DD') + ' 23:59:59']
            ];
            const model = self.get_model('reserve.order');
            const params = {
                model: 'reserve.order',
                fields: model.fields,
                domain: domain, //Today
                context: {}
            }
            let result = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context'])
            this.saveReserveOrders(result)
        },


        
    });
    
});
