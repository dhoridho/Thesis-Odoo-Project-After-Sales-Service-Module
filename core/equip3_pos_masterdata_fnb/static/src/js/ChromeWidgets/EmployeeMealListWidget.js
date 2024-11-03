odoo.define('equip3_pos_masterdata_fnb.EmployeeMealListWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class EmployeeMealListWidget extends PosComponent {
        async onClick() {
            $('.pos_new_section .custom_column.btn-employee-meal').removeClass('highlight');
            await this.showTempScreen( 'EmployeeMealList', { } );
        }

        mounted() {
            posbus.on('reload-employee-meal', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-employee-meal', this, null);
        }

        get isHidden() {
            return false;
            if (!this.env || !this.env.pos || !this.env.pos.config || (this.env && this.env.pos && this.env.pos.config && !this.env.pos.config.table_reservation_list)) {
                return true;
            } else {
                return false;
            }
        }

        get count() {
            let employee_meals = this.env.pos.db.get_employee_meal();
            if (this.env.pos &&  employee_meals.length > 0) {
                return employee_meals.length;
            } else {
                return 0;
            }
        }
    }

    EmployeeMealListWidget.template = 'EmployeeMealListWidget';
    Registries.Component.add(EmployeeMealListWidget);
    return EmployeeMealListWidget;
});
