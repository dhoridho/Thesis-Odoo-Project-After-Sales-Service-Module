$(document).ready(function(){
	
	$(".fa-link").click(function(){
	    $(".browse").click(); 
	});
	
	$("#category_section").multiselect();
	
	$(document).on("click", ".browse", function() {
	  var file = $(this).parents().find(".file");
	  file.trigger("click");
	});
	$('input[type="file"]').change(function(e) {
	  var fileName = e.target.files[0].name;
	  $("#file").val(fileName);
	
	  var reader = new FileReader();
	  reader.onload = function(e) {
	    // get loaded data and render thumbnail.
	    if($('#preview').length>0){
	    	document.getElementById("preview").src = e.target.result;
	    }
	    	
	  };
	  // read the image file as a data URL.
	  reader.readAsDataURL(this.files[0]);
	});
	var rowIdx = 0;
	$("#addBtn").on("click", function () {
        var rowCount = $(document).find("#contact_row row").length + 1;
		console.log(rowCount);
        rowIdx = rowIdx + 1;
        var vendorName = "vendor_c_name_" + String(rowIdx);
        var vendorEmail = "vendor_c_email_" + String(rowIdx);
        var vendorPhone = "vendor_c_phone_" + String(rowIdx);
        var productOptioons = '<option value="">Select Product</option>';
        var productOptioons = $(document).find("#js_id_product_list").html();
        var text =
			'<div class="row c_row '+
			String(rowIdx)+
			'">'+ '<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_name"><b>Name :</b></label>'+
				'<input type="text" class="form-control" ' +
				' name="'+
				vendorName+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_email"><b>Email :</b></label>'+
				'<input type="email" class="form-control" name="'+
				vendorEmail+
				'" required="required"/>'+
				'</div>'+
			    '</div>'+
'<div class="col-lg-4 col-sm-12">'+
			  '<div class="form-group">'+
				'<label for="vendor_contact_phone"><b>Phone :</b></label>'+
				'<div class="" style="display: flex;align-items: center;">'+
				'<input type="text" class="form-control" name="'+
				vendorPhone+
				'"/>'+
				'<button style="margin-left: 14px;margin-right: 7px;font-size: 22px;padding: 0;color: red;" class="btn remove" type="button"><i class="fa fa-trash"/></button>'+
				'</div>'+
				'</div>'+
			    '</div>'
        $("#contact_row").append(text);
    });
	
	$('#contact_row').on('click', ".remove",function() {
    	$(this).closest('.c_row').remove();
	});

});















