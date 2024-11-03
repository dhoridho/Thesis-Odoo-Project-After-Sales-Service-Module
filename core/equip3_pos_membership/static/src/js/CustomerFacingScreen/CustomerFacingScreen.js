// odoo.define('equip3_pos_membership.ClientScreenWidget', function (require) {
//     const models = require('point_of_sale.models');
//     const core = require('web.core');
//     const QWeb = core.qweb;

//     var _super_PosModel = models.PosModel.prototype;
//     models.PosModel = models.PosModel.extend({
//         initialize: function (session, attributes) {
//             _super_PosModel.initialize.apply(this, arguments); 
//         },
//         render_html_for_customer_facing_display: function () { // TODO: we add shop logo to customer screen
//             var self = this;
//             var order = this.get_order();
//             var rendered_html = this.config.customer_facing_display_html;
//             var get_image_promises = [];

//             if (order) {
//                 order.get_orderlines().forEach(function (orderline) {
//                     let product = orderline.product;
//                     let image_url = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + product.id;
//                     if (!product.image_base64) {
//                         get_image_promises.push(self._convert_product_img_to_base64(product, image_url));
//                     }
//                 });
//             }

//             // when all images are loaded in product.image_base64
//             return Promise.all(get_image_promises).then(function () {
//                 var rendered_order_lines = "";
//                 var rendered_payment_lines = "";
//                 var order_total_with_tax = self.format_currency(0);

//                 if (order) {
//                     rendered_order_lines = QWeb.render('CustomerFacingDisplayOrderLines', {
//                         'pos': self.env.pos,
//                         'orderlines': order.get_orderlines(),
//                     });
//                     rendered_payment_lines = QWeb.render('CustomerFacingDisplayPaymentLines', {
//                         'order': order,
//                         'pos': self.env.pos,
//                     });
//                     order_total_with_tax = self.format_currency(order.get_total_with_tax());
//                 }
//                 var $rendered_html = $(rendered_html);
//                 $rendered_html.find('.pos_orderlines_list').html(rendered_order_lines);
//                 $rendered_html.find('.pos-total').find('.pos_total-amount').html(order_total_with_tax);
//                 var pos_change_title = $rendered_html.find('.pos-change_title').text();
//                 $rendered_html.find('.pos-paymentlines').html(rendered_payment_lines);
//                 $rendered_html.find('.pos-change_title').text(pos_change_title);
//                 if (order && order.get_client()) {
//                     $rendered_html.find('.pos-total').find('.client-name').html(order.get_client().name);
//                     $rendered_html.find('.pos-total').find('.client-points').html(self.format_currency_no_symbol(order.get_client().pos_loyalty_point));
//                 }
//                 if (order) {
//                     let discount = self.format_currency(order.get_total_discount())
//                     $rendered_html.find('.pos-total').find('.pos_total-discount').html(discount);
//                 }
//                 if (order) {
//                     $rendered_html.find('.pos-total').find('.pos_total-taxes').html(self.format_currency(order.get_total_tax()));
//                 }
//                 const logo_base64 = self.get_logo();
//                 const image_html = '<img src="' + logo_base64 + '" class="logo-shop" style="width: 100%">';
//                 $rendered_html.find('.pos-company_logo').html(image_html);
//                 rendered_html = _.reduce($rendered_html, function (memory, current_element) {
//                     return memory + $(current_element).prop('outerHTML');
//                 }, "");

//                 rendered_html = QWeb.render('CustomerFacingDisplayHead', {
//                     origin: window.location.origin
//                 }) + rendered_html;
//                 return rendered_html;
//             });
//         },
//     });
// });
