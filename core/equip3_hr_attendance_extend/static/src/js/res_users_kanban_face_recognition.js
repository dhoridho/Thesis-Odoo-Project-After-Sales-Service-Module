odoo.define('equip3_hr_attendance_extend.res_users_kanban_face_recognition', function(require) {
    "use strict";

    var core = require('web.core');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

    var BtnDescriptionFieldOne2Many = FieldOne2Many.include({
        _create_image: function (record) {
            console.log('start create image')
            var data = record.data;
            return $.ajax({
                method: "POST",
                url: "/post/create-face-recognition-image",
                data: { 
                    'descriptor': data.descriptor,
                    'image_detection': data.image_detection,
                    'image': data.image,
                    'res_user_id': record.context.uid,
                    'name': data.name,
                    'sequence': data.sequence
                },
                async: false
            }).then(function () {
                Swal.close();
                console.log('descriptor success create');

                var json_data = $.parseJSON($.ajax({
                    method: "POST",
                    url: "/get/face-descriptor-amount",
                    data: {
                        "user_id": record.context.uid,
                    },
                    async: false
                }).responseText);
                $('.current_face_descriptor').text(json_data.current_res_users_image_amount);
            });
        },
    });
});