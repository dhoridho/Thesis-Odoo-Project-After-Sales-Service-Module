odoo.define('equip3_pos_user.CashierName', function (require) {
    'use strict';

    const CashierName = require('point_of_sale.CashierName');
    const Registries = require('point_of_sale.Registries');

    const UserCashierName = (CashierName) =>
        class extends CashierName {
            get getImage() {
                let cashier = this.env.pos.get('cashier');
                if (this.env.pos.config.module_pos_hr && this.env.pos.config.allowed_users && this.env.pos.config.allowed_users) {
                    if (cashier['id']) {
                        return `/web/image?model=res.users&id=${cashier['id']}&field=image_128&unique=1`;
                    } else {
                        return `/web/image?model=res.users&id=${cashier['user_id'][0]}&field=image_128&unique=1`;
                    }
                } else {
                    if (!cashier['id'] && cashier['user_id']) {
                        return `/web/image?model=res.users&id=${cashier['user_id'][0]}&field=image_128&unique=1`;
                    } else {
                        return `/web/image?model=res.users&id=${cashier['id']}&field=image_128&unique=1`;
                    }
                }
            }
            async selectCashier() {
                if (!this.env.pos.config.module_pos_hr) return;

                const list = this.env.pos.allowed_users
                    .filter((user) => user.id !== this.env.pos.get_cashier().id)
                    .map((user) => {
                        return {
                            id: user.id,
                            item: user,
                            label: user.name,
                            isSelected: false,
                            imageUrl: 'data:image/png;base64, ' + user['image_1920'],
                        };
                    });

                const user = await this.selectEmployee(list);
                if (user) {
                    user['is_user'] = true
                    this.env.pos.set_cashier(user);
                }
            }
        };

    Registries.Component.extend(CashierName, UserCashierName);

    return UserCashierName;
});
