odoo.define("equip3_purchase_vendor_portal.VendorPricelist", function(require){
    "use strict";

    var Session = require("web.session");

    $(document).ready(function(){
        $('input.vendor_pricelist_import').change(function(e) {
            var fileName = e.target.files[0].name;
            var reader = new FileReader();
            reader.onload = function(e) {
                Session.rpc("/my/vendor_pricelist_import", {
                    file: e.target.result.split(';base64,')[1],
                    file_name: fileName,
                }).then(function(result) {
                    if (result && result.message !== undefined) {
                        alert(result.message);
                    }
                    else {
                        window.location.reload();
                    }
                });
            };

            reader.readAsDataURL(this.files[0]);
        });
        if ($('textarea[name="rfq_note"]').data() !== undefined &&
            $('textarea[name="rfq_note"]').data().readonly) {
            $('textarea[name="rfq_note"]').summernote('disable');
        } else {
            $('textarea[name="rfq_note"]').summernote({
                toolbar: [
                    // [groupName, [list of button]]
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough', 'superscript', 'subscript']],
                    ['fontsize', ['fontsize']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['height', ['height']]
                ],
                popover: {
                  image: [
                    ['image', ['resizeFull', 'resizeHalf', 'resizeQuarter', 'resizeNone']],
                    ['float', ['floatLeft', 'floatRight', 'floatNone']],
                    ['remove', ['removeMedia']]
                  ],
                  link: [
                    ['link', ['linkDialogShow', 'unlink']]
                  ],
                  table: [
                    ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
                    ['delete', ['deleteRow', 'deleteCol', 'deleteTable']],
                  ],
                  air: [
                    ['color', ['color']],
                    ['font', ['bold', 'underline', 'clear']],
                    ['para', ['ul', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture']]
                  ]
                },
                height: 300,
            });

        }
        if ($('textarea[name="agreement_note"]').data() !== undefined &&
            $('textarea[name="agreement_note"]').data().readonly) {
            $('textarea[name="agreement_note"]').summernote('disable');
        } else {
            $('textarea[name="agreement_note"]').summernote({
                toolbar: [
                    // [groupName, [list of button]]
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough', 'superscript', 'subscript']],
                    ['fontsize', ['fontsize']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['height', ['height']]
                ],
                popover: {
                  image: [
                    ['image', ['resizeFull', 'resizeHalf', 'resizeQuarter', 'resizeNone']],
                    ['float', ['floatLeft', 'floatRight', 'floatNone']],
                    ['remove', ['removeMedia']]
                  ],
                  link: [
                    ['link', ['linkDialogShow', 'unlink']]
                  ],
                  table: [
                    ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
                    ['delete', ['deleteRow', 'deleteCol', 'deleteTable']],
                  ],
                  air: [
                    ['color', ['color']],
                    ['font', ['bold', 'underline', 'clear']],
                    ['para', ['ul', 'paragraph']],
                    ['table', ['table']],
                    ['insert', ['link', 'picture']]
                  ]
                },
                height: 300,
            });

        }
    });

});