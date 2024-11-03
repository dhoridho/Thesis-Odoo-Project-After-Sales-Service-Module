$(document).ready(function (require) {
	
    let selectedDeviceId;
    
    function decodeOnce(codeReader, selectedDeviceId) {
        codeReader
            .decodeFromInputVideoDevice(selectedDeviceId, "js_video_view_asset_stock_operations")
            .then((result) => {
                console.log(result);
                $('input[name="sh_asset_stock_barcode_mobile"]').val(result.text);
                $('input[name="sh_asset_stock_barcode_mobile"]').change();
                // $('input[name="scanned_value"]').val(result.text);
                // $('input[name="scanned_value"]').change();
                //RESET READER

                //HIDE VIDEO
                $("#js_id_sh_asset_stock_barcode_mobile_vid_div").hide();
                //HIDE STOP BUTTON
                $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").hide();
                //RESULT
                document.getElementById("js_id_sh_asset_stock_barcode_mobile_result").textContent = result.text;
                codeReader.reset();
            })
            .catch((err) => {
                console.error(err);
            });
    }

    function decodeContinuously(codeReader, selectedDeviceId) {
        codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, "js_video_view_asset_stock_operations", (result, err) => {
            if (result) {
                // properly decoded qr code
                console.log("Found QR code!", result);
                $('input[name="sh_asset_stock_barcode_mobile"]').val(result.text);
                // $('input[name="scanned_value"]').val(result.text);

                $('input[name="sh_asset_stock_barcode_mobile"]').change();
                // $('input[name="scanned_value"]').change();

                // $('input[name="scanned_value"]').val(result.text);
                // $('input[name="scanned_value"]').change();



                //RESULT
                document.getElementById("js_id_sh_asset_stock_barcode_mobile_result").textContent = result.text;
//                codeReader.reset();
                $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").click();
                //HIDE VIDEO
                $("#js_id_sh_asset_stock_barcode_mobile_vid_div").hide();

                //HIDE STOP BUTTON
                $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").hide();

            }

            if (err) {

                if (err instanceof ZXing.NotFoundException) {
                    console.log("No QR code found.");
                    //EMPTY INPUT
                    $('input[name="sh_asset_stock_barcode_mobile"]').val("");
                    $('input[name="sh_asset_stock_barcode_mobile"]').change();
                }

                if (err instanceof ZXing.ChecksumException) {
                    console.log("A code was found, but it's read value was not valid.");
                }

                if (err instanceof ZXing.FormatException) {
                    console.log("A code was found, but it was in a invalid format.");
                }
            }
        });
    }

    //HIDE STOP BUTTON (SAFETY IN XML WE ALSO DO AND HERE ALSO.)
    $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").hide();



    const codeReader = new ZXing.BrowserMultiFormatReader();
    //const codeReader = new ZXing.BrowserBarcodeReader()

    // console.log("ZXing code reader initialized");
    codeReader
        .getVideoInputDevices()
        .then(function (result) {
            //THEN METHOD START HERE
            //const sourceSelect = $("#js_id_sh_asset_stock_barcode_mobile_cam_select");
            const sourceSelect = document.getElementById("js_id_sh_asset_stock_barcode_mobile_cam_select");

            $('input[name="sh_asset_stock_barcode_mobile"]').val("");
            $('input[name="sh_asset_stock_barcode_mobile"]').change();

            _.each(result, function (item) {
                //self._add_filter(item.partner_id[0], item.partner_id[1], !active_partner, true);
                const sourceOption = document.createElement("option");
                sourceOption.text = item.label;
                sourceOption.value = item.deviceId;
                sourceSelect.appendChild(sourceOption);
            });

        	$(document).on('change', '#js_id_sh_asset_stock_barcode_mobile_cam_select', function(ev) {
        		  // Does some stuff and logs the event to the console
        		var cameraSelect = $(ev.currentTarget);
        		selectedDeviceId = cameraSelect.val(); 
        		//RESET READER
                codeReader.reset();
                // trigger start button click to render video with selected camera.
        		$("#js_id_sh_asset_stock_barcode_mobile_reset_btn").click();
        		$("#js_id_sh_asset_stock_barcode_mobile_start_btn").click();
                
                
        	});
            
            $(document).on("click", "#js_id_sh_asset_stock_barcode_mobile_start_btn", function (event) {
                //EMPTY INPUT
                $('input[name="sh_asset_stock_barcode_mobile"]').val("");
                $('input[name="sh_asset_stock_barcode_mobile"]').change();
                //SHOW VIDEO
                $("#js_id_sh_asset_stock_barcode_mobile_vid_div").show();
                //SHOW STOP BUTTON
                $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").show();

                //CALL METHOD
                //CONTINUOUS SCAN OR NOT.
                decodeOnce(codeReader, selectedDeviceId);
            });
            
            $(document).on("click", "#js_id_sh_asset_stock_barcode_mobile_reset_btn", function () {
                console.log("STOP CAMERA");
                document.getElementById("js_id_sh_asset_stock_barcode_mobile_result").textContent = "";

                //EMPTY VALUE
                $('input[name="sh_asset_stock_barcode_mobile"]').val("");
                $('input[name="sh_asset_stock_barcode_mobile"]').change();

                //RESET READER
                codeReader.reset();

                //HIDE VIDEO
                $("#js_id_sh_asset_stock_barcode_mobile_vid_div").hide();

                //HIDE STOP BUTTON
                $("#js_id_sh_asset_stock_barcode_mobile_reset_btn").hide();
            });
            
        })
        .catch(function (reason) {
            console.log("Error ==>" + reason);
        });
});
